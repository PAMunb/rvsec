"""
FastBot model-based testing tool implementation.

This module provides integration with the FastBot Android testing framework,
enabling model-based testing with reinforcement learning capabilities.
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


class FastBotTool(AbstractTool):
    """
    FastBot model-based testing tool with reinforcement learning capabilities.

    ### Architectural Decisions:
    - Inherits directly from AbstractTool for simplified architecture
    - Implements model-based testing with reinforcement learning algorithms
    - Provides intelligent exploration using machine learning techniques
    - Uses JAR-based execution model for cross-platform compatibility
    - Supports multiple learning strategies and configuration options
    - Integrates with rv-android-core infrastructure for error handling and logging

    ### Role in the System:
    - Serves as an AI-guided testing tool for intelligent Android app exploration
    - Provides model-based testing with adaptive learning capabilities
    - Enables intelligent exploration using reinforcement learning algorithms
    - Supports both JCA cryptography detection and generic monitored operations testing
    - Facilitates advanced testing through machine learning-guided exploration

    ### Key Features:
    - Model-based testing with reinforcement learning
    - Intelligent action selection and strategy adaptation
    - Configurable learning parameters and exploration strategies
    - JAR-based execution for cross-platform compatibility
    - Integration with Android Debug Bridge (ADB) for device communication

    ### Tool Variants:
    FastBot supports different learning modes as variants:
    - conservative: Conservative exploration with safe actions
    - aggressive: Aggressive exploration with diverse actions
    - balanced: Balanced exploration strategy
    """

    # Simplified tool specification
    TOOL_SPEC = ToolSpec.create_builtin_spec(
        name="fastbot",
        description="FastBot model-based testing tool with reinforcement learning capabilities",
        url="https://github.com/bytedance/Fastbot_Android",
        version="1.0.0",
        process_pattern="fastbot"
    )

    # Available exploration strategies
    AVAILABLE_STRATEGIES = [
        'conservative', 'aggressive', 'balanced', 'random', 'model_based'
    ]

    def __init__(self, name: str = None, description: str = None, process_pattern: str = None):
        """
        Initialize the FastBot tool with rv-android-core infrastructure.
        """
        super().__init__(
            name=name or self.TOOL_SPEC.name,
            description=description or self.TOOL_SPEC.description,
            process_pattern=process_pattern or self.TOOL_SPEC.process_pattern
        )

        # Initialize rv-android-core infrastructure components
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_tools.builtin.fastbot",
            {CONTEXT_COMPONENT: "FastBotTool"}
        )
        self.error_handler = ErrorHandler.get_instance()

        # Default FastBot configuration
        self.config = {
            "max_step": 10000,               # Maximum exploration steps
            "device_serial": None,           # Device serial number
            "strategy": "balanced",          # Exploration strategy
            "fastbot_thirdpart_jar": None,   # FastBot thirdpart jar path
            "framework_jar": None,           # Framework jar path
            "monkeyq_jar": None,             # MonkeyQ jar path
            "throttle": 500,                 # Throttle between actions (ms)
            "debug_mode": False,             # Enable debug mode
            "timeout": 3600,                 # Execution timeout in seconds
            "learning_rate": 0.1,            # Learning rate for RL
            "exploration_rate": 0.2,         # Exploration rate (epsilon)
            "model_update_frequency": 100    # Model update frequency
        }

        self.logger.info("Initialized FastBot tool for model-based exploration")

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure FastBot-specific parameters.

        Supported configuration options:
        - max_step: Maximum exploration steps
        - device_serial: Device serial number
        - strategy: Exploration strategy
        - throttle: Throttle between actions in milliseconds
        - debug_mode: Enable debug mode
        - timeout: Execution timeout in seconds
        - learning_rate: Learning rate for reinforcement learning
        - exploration_rate: Exploration rate (epsilon)
        - model_update_frequency: Model update frequency

        Args:
            config: Configuration dictionary with FastBot parameters
        """
        if not config:
            return

        # Update max steps
        if 'max_step' in config:
            try:
                steps = int(config['max_step'])
                if steps > 0:
                    self.config['max_step'] = steps
                    self.logger.debug(f"Set FastBot max steps to: {steps}")
                else:
                    self.logger.warning("Max steps must be positive")
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid max_step value: {config['max_step']}")

        # Update device serial
        if 'device_serial' in config:
            self.config['device_serial'] = config['device_serial']
            self.logger.debug(f"Set FastBot device serial to: {config['device_serial']}")

        # Update exploration strategy
        if 'strategy' in config:
            strategy = config['strategy']
            if strategy not in self.AVAILABLE_STRATEGIES:
                self.logger.warning(f"Invalid strategy '{strategy}'. Using default 'balanced'")
                self.logger.warning(f"Available strategies: {self.AVAILABLE_STRATEGIES}")
            else:
                self.config['strategy'] = strategy
                self.logger.debug(f"Set FastBot strategy to: {strategy}")

        # Update throttle
        if 'throttle' in config:
            try:
                throttle = int(config['throttle'])
                if throttle >= 0:
                    self.config['throttle'] = throttle
                    self.logger.debug(f"Set FastBot throttle to: {throttle}ms")
                else:
                    self.logger.warning("Throttle must be non-negative")
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid throttle value: {config['throttle']}")

        # Update timeout
        if 'timeout' in config:
            try:
                timeout = int(config['timeout'])
                if timeout > 0:
                    self.config['timeout'] = timeout
                    self.logger.debug(f"Set FastBot timeout to: {timeout}s")
                else:
                    self.logger.warning("Timeout must be positive")
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid timeout value: {config['timeout']}")

        # Update learning parameters
        learning_params = ['learning_rate', 'exploration_rate']
        for param in learning_params:
            if param in config:
                try:
                    value = float(config[param])
                    if 0.0 <= value <= 1.0:
                        self.config[param] = value
                        self.logger.debug(f"Set FastBot {param} to: {value}")
                    else:
                        self.logger.warning(f"{param} must be between 0.0 and 1.0")
                except (ValueError, TypeError):
                    self.logger.warning(f"Invalid {param} value: {config[param]}")

        # Update model update frequency
        if 'model_update_frequency' in config:
            try:
                freq = int(config['model_update_frequency'])
                if freq > 0:
                    self.config['model_update_frequency'] = freq
                    self.logger.debug(f"Set FastBot model update frequency to: {freq}")
                else:
                    self.logger.warning("Model update frequency must be positive")
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid model_update_frequency value: {config['model_update_frequency']}")

        # Update boolean flags
        if 'debug_mode' in config:
            self.config['debug_mode'] = bool(config['debug_mode'])
            self.logger.debug(f"Set FastBot debug mode to: {self.config['debug_mode']}")

        # Update jar paths
        jar_params = ['fastbot_thirdpart_jar', 'framework_jar', 'monkeyq_jar']
        for param in jar_params:
            if param in config:
                self.config[param] = config[param]
                self.logger.debug(f"Set FastBot {param} to: {config[param]}")

    @ErrorHandler.handle_errors(
        component="FastBotTool",
        phase="execute_tool_specific_logic"
    )
    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
        """
        Execute FastBot testing with configured parameters.

        ### Execution Workflow:
        1. Resolve FastBot jar file locations
        2. Prepare model and learning configuration
        3. Execute FastBot with specified parameters
        4. Capture execution output and learning metrics
        5. Process results and model updates

        Args:
            task: Task configuration containing timeout and other parameters
            app: Application under test with package name and metadata
        """
        self.logger.info(f"Executing FastBot tool for {app.package_name}")
        self.logger.debug(f"Strategy: {self.config['strategy']}, Max steps: {self.config['max_step']}")

        # Get timeout from task configuration
        timeout_in_seconds = getattr(task.config, 'timeout', self.config['timeout'])
        
        self.logger.info(f"FastBot execution timeout: {timeout_in_seconds} seconds")

        # Create output directory for FastBot results
        output_dir = os.path.join(os.path.dirname(task.result.trace_file), "fastbot_output")
        os.makedirs(output_dir, exist_ok=True)

        # Resolve FastBot jar files
        jar_paths = self._resolve_fastbot_jars()

        # Build FastBot command
        fastbot_cmd = self._build_fastbot_command(app, jar_paths, output_dir, timeout_in_seconds)
        
        # Build command string for logging
        cmd_str = f"{fastbot_cmd.command} {' '.join(fastbot_cmd.args)}"
        self.logger.debug(f"FastBot command: {cmd_str}")

        # Execute FastBot testing
        try:
            self.logger.info(f"Starting FastBot execution for {app.package_name}")
            result = fastbot_cmd.invoke()
            
            # Write result to trace file
            with open(task.result.trace_file, 'w') as trace_file:
                trace_file.write(f"FastBot execution completed\n")
                trace_file.write(f"Strategy: {self.config['strategy']}\n")
                trace_file.write(f"Max steps: {self.config['max_step']}\n")
                trace_file.write(f"Learning rate: {self.config['learning_rate']}\n")
                trace_file.write(f"Output directory: {output_dir}\n")
                trace_file.write(f"Command: {cmd_str}\n")
                if result.stdout:
                    trace_file.write(f"STDOUT:\n{result.stdout}\n")
                if result.stderr:
                    trace_file.write(f"STDERR:\n{result.stderr}\n")
            
            self.logger.info("FastBot execution completed successfully")
            
        except Exception as e:
            self.logger.error(f"FastBot execution failed: {str(e)}")
            # Write error information to trace file
            with open(task.result.trace_file, 'w') as trace_file:
                trace_file.write(f"FastBot execution error: {str(e)}\n")
                trace_file.write(f"Command: {cmd_str}\n")
            raise

    def _resolve_fastbot_jars(self) -> Dict[str, str]:
        """
        Resolve paths to FastBot jar files.

        Returns:
            Dictionary with paths to required jar files

        Raises:
            FileNotFoundError: If required jar files are not found
        """
        jar_paths = {}
        
        # Required jar files
        required_jars = {
            'fastbot_thirdpart': 'fastbot-thirdpart.jar',
            'framework': 'framework.jar',
            'monkeyq': 'monkeyq.jar'
        }

        for jar_key, jar_filename in required_jars.items():
            config_key = f"{jar_key}_jar"
            
            # Check configured path first
            if self.config.get(config_key) and os.path.isfile(self.config[config_key]):
                jar_paths[jar_key] = self.config[config_key]
                continue

            # Search in common locations
            search_paths = [
                os.path.join(os.path.dirname(__file__), jar_filename),
                os.path.join('/opt/rv-android/tools/fastbot', jar_filename),
                os.path.join('./tools/fastbot', jar_filename)
            ]

            found = False
            for path in search_paths:
                if path and os.path.isfile(path):
                    jar_paths[jar_key] = path
                    self.logger.debug(f"Found {jar_filename} at: {path}")
                    found = True
                    break

            if not found:
                raise FileNotFoundError(f"FastBot jar file {jar_filename} not found. Please ensure FastBot is properly installed.")

        return jar_paths

    def _build_fastbot_command(self, app: App, jar_paths: Dict[str, str], output_dir: str, timeout_seconds: int) -> Command:
        """
        Build the FastBot command with configured parameters.

        Args:
            app: Application under test
            jar_paths: Dictionary with paths to jar files
            output_dir: Output directory for FastBot results
            timeout_seconds: Command execution timeout

        Returns:
            Configured Command object for FastBot execution
        """
        # Start building command arguments for FastBot execution
        cmd_args = [
            "-cp", f"{jar_paths['fastbot_thirdpart']}:{jar_paths['framework']}:{jar_paths['monkeyq']}",
            "com.android.commands.monkey.Monkey",
            "-p", app.package_name,
            "--agent", "reuseq",
            "--running-minutes", str(int(self.config['timeout'] / 60)),
            "--throttle", str(self.config['throttle']),
            "--bugreport"
        ]

        # Add device serial if specified
        if self.config["device_serial"]:
            cmd_args.extend(["-s", self.config["device_serial"]])

        # Add strategy-specific parameters
        strategy = self.config["strategy"]
        if strategy == "conservative":
            cmd_args.extend(["--act-blacklist-file", "conservative_blacklist.txt"])
        elif strategy == "aggressive":
            cmd_args.extend(["--act-whitelist-file", "aggressive_whitelist.txt"])

        # Add max steps
        cmd_args.extend(["--max-step", str(self.config["max_step"])])

        # Add debug mode if enabled
        if self.config["debug_mode"]:
            cmd_args.append("--verbose")

        # Add learning parameters
        cmd_args.extend([
            "--learning-rate", str(self.config["learning_rate"]),
            "--exploration-rate", str(self.config["exploration_rate"]),
            "--model-update-freq", str(self.config["model_update_frequency"])
        ])

        return Command("java", cmd_args, timeout_seconds)

    def get_available_strategies(self) -> List[str]:
        """
        Get list of available exploration strategies.

        Returns:
            List of available strategy names
        """
        return self.AVAILABLE_STRATEGIES.copy()

    def get_tool_info(self) -> dict:
        """
        Get comprehensive FastBot tool information.

        Returns:
            Dictionary with tool information and current configuration
        """
        info = super().get_tool_info()
        info.update({
            "tool_spec": self.TOOL_SPEC.to_dict(),
            "available_strategies": self.get_available_strategies(),
            "current_strategy": self.config["strategy"],
            "current_max_step": self.config["max_step"],
            "learning_rate": self.config["learning_rate"],
            "exploration_rate": self.config["exploration_rate"],
            "version": self.TOOL_SPEC.version,
            "url": self.TOOL_SPEC.url
        })
        return info


# Function to register FastBot variants
def register_fastbot_variants(registry):
    """
    Register FastBot variants in the tool registry.
    
    Args:
        registry: ToolRegistry instance
    """
    # Register exploration strategy variants
    variants = {
        "conservative": {"strategy": "conservative", "exploration_rate": 0.1},
        "aggressive": {"strategy": "aggressive", "exploration_rate": 0.3},
        "balanced": {"strategy": "balanced", "exploration_rate": 0.2},
        "model_based": {"strategy": "model_based", "learning_rate": 0.15, "model_update_frequency": 50}
    }
    
    for variant_name, config in variants.items():
        registry.register_variant("fastbot", variant_name, config)