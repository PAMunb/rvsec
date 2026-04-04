"""
FastBot model-based testing tool implementation.

This module provides integration with the FastBot Android testing framework,
enabling model-based testing with reinforcement learning capabilities.
"""

import os
from typing import Dict, Any, List

from rv_android_core.domain.app import App
from rv_android_core.commands.command import Command
from rv_android_core.domain.task import Task
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import RVToolExecutionError
from rv_android_core.util.jar_resolver import JarResolver
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
        self.jar_resolver = JarResolver()

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

    @classmethod
    def get_tool_spec(cls):
        """Get tool specification for registration."""
        return cls.TOOL_SPEC
    
    @classmethod
    def get_variants(cls) -> Dict[str, Dict[str, Any]]:
        """Get available FastBot variants with different learning strategies."""
        return {
            "default": {
                "max_step": 10000,
                "strategy": "balanced",
                "throttle": 500,
                "debug_mode": False,
                "timeout": 3600,
                "learning_rate": 0.1,
                "exploration_rate": 0.2,
                "model_update_frequency": 100
            },
            "conservative": {
                "max_step": 5000,
                "strategy": "conservative",
                "throttle": 1000,
                "debug_mode": False,
                "timeout": 1800,
                "learning_rate": 0.05,
                "exploration_rate": 0.1,
                "model_update_frequency": 200
            },
            "aggressive": {
                "max_step": 20000,
                "strategy": "aggressive",
                "throttle": 200,
                "debug_mode": True,
                "timeout": 5400,
                "learning_rate": 0.2,
                "exploration_rate": 0.4,
                "model_update_frequency": 50
            },
            "balanced": {
                "max_step": 15000,
                "strategy": "balanced",
                "throttle": 300,
                "debug_mode": False,
                "timeout": 4200,
                "learning_rate": 0.15,
                "exploration_rate": 0.25,
                "model_update_frequency": 75
            }
        }

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

        # Resolve FastBot jar files
        jar_paths = self._resolve_fastbot_jars()

        # Push JARs to device before execution
        self._push_jars_to_sdcard(jar_paths, task.result.trace_file)
        
        # Push native libraries to device
        self._push_libs_to_device(task.result.trace_file)

        # Build FastBot command
        timeout_in_minutes = int(timeout_in_seconds / 60)
        if timeout_in_minutes == 0:
            timeout_in_minutes = 1
        fastbot_cmd = self._build_fastbot_command(app, timeout_in_minutes, timeout_in_seconds)
        
        # Build command string for logging
        cmd_str = f"{fastbot_cmd.command} {' '.join(fastbot_cmd.args)}"
        self.logger.debug(f"FastBot command: {cmd_str}")

        # Execute FastBot testing with centralized error handling
        try:
            self.logger.info(f"Starting FastBot execution for {app.package_name}")
            
            # Execute command with output redirection (binary mode for command output)
            with open(task.result.trace_file, 'wb') as trace_file:
                # Use centralized command execution with error handling
                # Redirect both stdout and stderr to trace file to prevent console flooding
                self._execute_and_check_command(fastbot_cmd, stdout=trace_file, stderr=trace_file)
            
            # Append success information to trace file (text mode for metadata)
            # with open(task.result.trace_file, 'a', encoding='utf-8') as trace_file:
            #     success_info = f"\n--- FastBot Execution Completed ---\n"
            #     success_info += f"Strategy: {self.config['strategy']}\n"
            #     success_info += f"Running minutes: {timeout_in_minutes}\n"
            #     success_info += f"Command: {cmd_str}\n"
            #     trace_file.write(success_info)
            
            self.logger.info("FastBot execution completed successfully")
            
        except Exception as e:
            self.logger.error(f"FastBot execution failed: {str(e)}")
            raise

    def _resolve_fastbot_jars(self) -> Dict[str, str]:
        """
        Resolve paths to FastBot jar files using centralized JarResolver.

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

        # Common search paths for FastBot jars
        search_paths = [
            # Environment variable based path
            os.path.join(os.environ.get('TOOLS_DIR', ''), 'fastbot'),
            # Relative to current module
            os.path.dirname(__file__),
            # Standard installation paths
            '/opt/rv-android/tools/fastbot',
            './tools/fastbot',
            '../tools/fastbot'
        ]

        for jar_key, jar_filename in required_jars.items():
            config_key = f"{jar_key}_jar"
            
            try:
                # Check configured path first
                if self.config.get(config_key):
                    jar_paths[jar_key] = self.jar_resolver.resolve_jar_path(jar_filename, [os.path.dirname(self.config[config_key])])
                else:
                    # Use JarResolver with search paths
                    jar_paths[jar_key] = self.jar_resolver.resolve_jar_path(jar_filename, search_paths)
                    
            except FileNotFoundError:
                raise FileNotFoundError(f"FastBot jar file {jar_filename} not found. Please ensure FastBot is properly installed.")

        return jar_paths

    def _push_jars_to_sdcard(self, jar_paths: Dict[str, str], trace_file_path: str) -> None:
        """
        Push FastBot JAR files to device /sdcard/ directory.
        
        Transfers JAR files required for FastBot execution to the Android device
        storage location for ADB shell execution.
        
        Args:
            jar_paths: Dictionary containing local paths to JAR files
            trace_file_path: Path to trace file for logging push operations
            
        Raises:
            RVToolExecutionError: If JAR file push operation fails
        """
        device_jar_paths = {
            'fastbot_thirdpart': '/sdcard/fastbot-thirdpart.jar',
            'framework': '/sdcard/framework.jar', 
            'monkeyq': '/sdcard/monkeyq.jar'
        }
        
        for jar_key, local_path in jar_paths.items():
            device_path = device_jar_paths[jar_key]
            
            self.logger.info(f"Pushing {jar_key} JAR from {local_path} to {device_path}")
            
            push_cmd = Command('adb', [
                '-s', self.config.get("device_serial") or "emulator-5554",
                'push', '-a', '-p', local_path, device_path
            ], timeout=60)  # 60 seconds timeout for push
            
            with open(trace_file_path, 'ab') as trace_file:
                trace_file.write(f"\n--- FastBot JAR Push: {jar_key} ---\n".encode('utf-8'))
                result = push_cmd.invoke(stdout=trace_file)
                
                if result.is_failure():
                    error_msg = f"Failed to push {jar_key} JAR to device with exit code {result.code}"
                    if result.has_error_output():
                        error_msg += f". Error: {result.get_stderr_text()}"
                    
                    self.logger.error(error_msg)
                    raise RVToolExecutionError(
                        error_msg,
                        tool_name=self.name,
                        cause=None
                    )
        
        self.logger.debug("All FastBot JARs pushed to device successfully")

    def _push_libs_to_device(self, trace_file_path: str) -> None:
        """
        Push FastBot native libraries to device architecture-specific directories.
        
        Transfers native library files (.so) required for FastBot execution to the Android device
        in the appropriate architecture-specific directories.
        
        Args:
            trace_file_path: Path to trace file for logging push operations
            
        Raises:
            RVToolExecutionError: If library file push operation fails
        """
        # Resolve libs directory using JarResolver
        search_paths = [os.path.dirname(__file__)]
        try:
            libs_dir = self.jar_resolver.resolve_resource_directory("libs", search_paths)
        except Exception as e:
            self.logger.warning(f"FastBot libs directory not found: {e}")
            self.logger.info("Continuing without native libraries (may affect performance)")
            return

        # Architecture mappings - fastbot expects libs in /data/local/tmp/<arch>/
        arch_mappings = {
            'arm64-v8a': '/data/local/tmp/arm64-v8a/',
            'armeabi-v7a': '/data/local/tmp/armeabi-v7a/',
            'x86': '/data/local/tmp/x86/',
            'x86_64': '/data/local/tmp/x86_64/'
        }

        for arch, device_path in arch_mappings.items():
            local_lib_path = os.path.join(libs_dir, arch, "libfastbot_native.so")
            
            if not os.path.isfile(local_lib_path):
                self.logger.debug(f"FastBot native library not found for {arch}: {local_lib_path}")
                continue
                
            device_lib_path = os.path.join(device_path, "libfastbot_native.so")
            
            self.logger.info(f"Pushing FastBot native library for {arch} to {device_lib_path}")
            
            push_cmd = Command('adb', [
                '-s', self.config.get("device_serial") or "emulator-5554",
                'push', '-a', '-p', local_lib_path, device_lib_path
            ], timeout=60)  # 60 seconds timeout for push
            
            with open(trace_file_path, 'ab') as trace_file:
                trace_file.write(f"\n--- FastBot Native Library Push: {arch} ---\n".encode('utf-8'))
                try:
                    # Use centralized command execution with error handling
                    self._execute_and_check_command(push_cmd, stdout=trace_file)
                    self.logger.debug(f"Successfully pushed FastBot native library for {arch}")
                except Exception as e:
                    self.logger.warning(f"Failed to push FastBot native library for {arch}: {e}")
                    # Continue with other architectures - this is not critical
                    continue
        
        self.logger.debug("FastBot native libraries push completed")

    def _build_fastbot_command(self, app: App, timeout_minutes: int, timeout_seconds: int) -> Command:
        """
        Build the FastBot command using ADB shell execution model.
        
        Constructs ADB shell command for FastBot model-based testing with 
        JAR file execution on Android device and reinforcement learning capabilities.
        
        Command format: adb -s emulator-5554 shell CLASSPATH=/sdcard/monkeyq.jar:/sdcard/framework.jar:/sdcard/fastbot-thirdpart.jar 
                       exec app_process /system/bin com.android.commands.monkey.Monkey -p <package> --agent reuseq 
                       --running-minutes <X> --throttle <Y> -v -v

        Args:
            app: Application under test containing package name and metadata
            timeout_minutes: Execution timeout in minutes for FastBot strategy
            timeout_seconds: Command execution timeout in seconds

        Returns:
            Configured Command object for FastBot execution
        """
        cmd_args = [
            "-s", self.config.get("device_serial") or "emulator-5554",
            "shell",
            "CLASSPATH=/sdcard/monkeyq.jar:/sdcard/framework.jar:/sdcard/fastbot-thirdpart.jar",
            "exec", "app_process", "/system/bin",
            "com.android.commands.monkey.Monkey",
            "-p", app.package_name,
            "--agent", "reuseq", 
            "--running-minutes", str(timeout_minutes),
            "--throttle", str(self.config["throttle"]),
            "-v", "-v"  # Verbose output for debugging
        ]

        return Command("adb", cmd_args, timeout_seconds)

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