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

    def __init__(self, name: str = None, description: str = None, process_pattern: str = None):
        """
        Initialize the DroidBot tool with rv-android-core infrastructure.
        """
        super().__init__(
            name=name or self.TOOL_SPEC.name,
            description=description or self.TOOL_SPEC.description,
            process_pattern=process_pattern or self.TOOL_SPEC.process_pattern
        )

        # Initialize rv-android-core infrastructure components
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_tools.builtin.droidbot",
            {CONTEXT_COMPONENT: "DroidBotTool"}
        )

        # Default DroidBot configuration
        self.config = {
            "policy": "dfs_naive",  # Exploration policy
            "count": 1000,  # Number of events to generate
            "timeout": 3600,  # Timeout in seconds
            "interval": 3,  # Interval between events
            "device_serial": None,  # Device serial number
            "keep_app": False,  # Keep app installed after testing
            "keep_env": False,  # Keep environment after testing
            "debug_mode": False,  # Enable debug mode
            "random_input": False,  # Enable random input generation
            "script_path": None,  # Path to script for guided testing
            "profiling_method": "none",  # Profiling method
            "grant_perm": True,  # Grant permissions automatically
            "enable_accessibility_hard": False,  # Enable accessibility service
            "master": None,  # Master device for distributed testing
            "humanoid": None,  # Humanoid model for input generation
            "ignore_ad": True,  # Ignore advertisement elements
            "replay_output": None  # Replay output directory
        }

        self.logger.info("Initialized DroidBot tool for UI exploration")

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure DroidBot-specific parameters.
        
        Supported configuration options:
        - policy: Exploration policy (dfs_naive, dfs_greedy, bfs_naive, bfs_greedy, random)
        - count: Number of events to generate
        - timeout: Timeout in seconds
        - interval: Interval between events
        - device_serial: Device serial number
        - keep_app: Keep app installed after testing
        - keep_env: Keep environment after testing
        - debug_mode: Enable debug mode
        - random_input: Enable random input generation
        - grant_perm: Grant permissions automatically
        - ignore_ad: Ignore advertisement elements
        
        Args:
            config: Configuration dictionary with DroidBot parameters
        """
        if not config:
            return

        # Update exploration policy
        if 'policy' in config:
            policy = config['policy']
            if policy not in self.AVAILABLE_POLICIES:
                self.logger.warning(f"Invalid policy '{policy}'. Using default 'dfs_naive'")
                self.logger.warning(f"Available policies: {self.AVAILABLE_POLICIES}")
            else:
                self.config['policy'] = policy
                self.logger.debug(f"Set DroidBot policy to: {policy}")

        # Update event count
        if 'count' in config:
            try:
                count = int(config['count'])
                if count > 0:
                    self.config['count'] = count
                    self.logger.debug(f"Set DroidBot event count to: {count}")
                else:
                    self.logger.warning("Event count must be positive")
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid count value: {config['count']}")

        # Update timeout
        if 'timeout' in config:
            try:
                timeout = int(config['timeout'])
                if timeout > 0:
                    self.config['timeout'] = timeout
                    self.logger.debug(f"Set DroidBot timeout to: {timeout}s")
                else:
                    self.logger.warning("Timeout must be positive")
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid timeout value: {config['timeout']}")

        # Update interval
        if 'interval' in config:
            try:
                interval = int(config['interval'])
                if interval >= 0:
                    self.config['interval'] = interval
                    self.logger.debug(f"Set DroidBot interval to: {interval}s")
                else:
                    self.logger.warning("Interval must be non-negative")
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid interval value: {config['interval']}")

        # Update device serial
        if 'device_serial' in config:
            self.config['device_serial'] = config['device_serial']
            self.logger.debug(f"Set DroidBot device serial to: {config['device_serial']}")

        # Update boolean flags
        boolean_flags = [
            'keep_app', 'keep_env', 'debug_mode', 'random_input',
            'grant_perm', 'enable_accessibility_hard', 'ignore_ad'
        ]

        for flag in boolean_flags:
            if flag in config:
                self.config[flag] = bool(config[flag])
                self.logger.debug(f"Set DroidBot {flag} to: {self.config[flag]}")

        # Update string parameters
        string_params = ['script_path', 'profiling_method', 'master', 'humanoid', 'replay_output']
        for param in string_params:
            if param in config:
                self.config[param] = config[param]
                self.logger.debug(f"Set DroidBot {param} to: {config[param]}")

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
        
        Command format: droidbot -d emulator-5554 -a <apk> -policy <policy> -count 10000000000 -timeout <timeout> -ignore_ad -is_emulator
        
        Args:
            app: Application under test containing APK path and metadata
            timeout_seconds: Command execution timeout in seconds
            
        Returns:
            Configured Command object for DroidBot execution
        """
        cmd_args = [
            "-d", "emulator-5554",  # Target device specification
            "-a", app.path,
            "-policy", self.config["policy"],  # Exploration policy configuration
            "-count", "10000000000",  # High event count for comprehensive exploration
            "-timeout", str(timeout_seconds),
            "-ignore_ad",  # Ignore advertisement elements
            "-is_emulator"  # Emulator-specific optimizations
        ]

        return Command("droidbot", cmd_args, timeout_seconds)

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


# Função para registrar variantes do DroidBot
def register_droidbot_variants(registry):
    """
    Register DroidBot variants in the tool registry.
    
    Args:
        registry: ToolRegistry instance
    """
    # Register common exploration policy variants
    variants = {
        "bfs_greedy": {"policy": "bfs_greedy"},
        "dfs_greedy": {"policy": "dfs_greedy"},
        "bfs_naive": {"policy": "bfs_naive"},
        "dfs_naive": {"policy": "dfs_naive"},
        "random": {"policy": "random"}
    }

    for variant_name, config in variants.items():
        registry.register_variant("droidbot", variant_name, config)
