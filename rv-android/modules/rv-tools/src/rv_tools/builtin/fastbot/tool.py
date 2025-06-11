"""
FastBot testing tool implementation for monitored operations.

FastBot is a model-based Android testing tool that uses reinforcement learning
to intelligently explore application GUI transitions and discover stability issues.
"""

import os
from typing import Any

from rv_android_core.app import App
from rv_android_core.commands.command import Command
from rv_android_core.tools.configurable_tool import ConfigurableTool
from rv_android_core.tools.tool_spec import ToolSpec, ToolType, ToolCategory
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT


class FastBotTool(ConfigurableTool):
    """
    FastBot testing tool for model-based monitored operations exploration.

    ### Architectural Decisions:
    - Extends ConfigurableTool for standardized configuration handling
    - Provides clean interface to FastBot reinforcement learning framework
    - Supports comprehensive customization of FastBot parameters
    - Implements model-based GUI exploration with adaptive strategies
    - Integrates with RV-Android monitored operations infrastructure

    ### Role in the System:
    - Integrates FastBot Android testing tool into monitored operations framework
    - Enables model-based testing with reinforcement learning capabilities
    - Provides intelligent GUI exploration for comprehensive coverage
    - Supports adaptive exploration strategies based on application behavior
    - Facilitates discovery of stability issues and performance problems

    ### Key Considerations:
    - Supports multiple exploration agents (reuseq, random, model-based)
    - Manages complex multi-jar deployment and native library setup
    - Provides configurable throttle and timeout management
    - Integrates with monitored operations instrumentation for coverage tracking
    - Handles device communication and file transfer operations

    ### Integration Strategy:
    - Compatible with experiment framework and task management
    - Supports configuration through ToolRegistry and ToolFactory
    - Enables dynamic parameter customization per experiment
    - Provides standardized logging and error handling
    - Facilitates result collection and analysis integration

    ### Performance and Scalability:
    - Optimized for intelligent state space exploration using RL
    - Supports configurable exploration parameters and strategies
    - Enables efficient model-based testing with adaptive exploration
    - Adaptable to different application complexity and behavior patterns
    - Minimizes overhead through smart exploration and resource management
    """

    # FastBot tool specification
    TOOL_SPEC = ToolSpec.create_builtin_spec(
        name="fastbot",
        description="Model-based Android testing with reinforcement learning for GUI exploration",
        category=ToolCategory.MODEL_BASED,
        version="1.0.0",
        process_pattern="com.android.commands.monkey",
        capabilities=[
            "model_based_testing",
            "reinforcement_learning", 
            "adaptive_exploration",
            "gui_modeling",
            "intelligent_navigation",
            "stability_testing",
            "performance_analysis"
        ]
    )

    def __init__(self):
        """
        Initialize FastBot tool with default configuration and rv-android-core infrastructure.
        
        ### Infrastructure Integration:
        - Sets up standardized logging with FastBot-specific context
        - Initializes error handler for comprehensive error management
        - Configures FastBot-specific parameters and RL settings
        - Establishes integration with monitored operations framework
        """
        super().__init__(
            name=self.TOOL_SPEC.name,
            description=self.TOOL_SPEC.description,
            process_pattern=self.TOOL_SPEC.process_pattern
        )

        # Initialize rv-android-core infrastructure components
        self._logging_manager = LoggingManager.get_instance()
        self.logger = self._logging_manager.get_logger(
            "tools.fastbot", 
            {CONTEXT_COMPONENT: "FastBotTool"}
        )
        self.error_handler = ErrorHandler.get_instance()

        # Default FastBot configuration
        self.config = {
            "throttle": 100,                      # Delay between events (ms)
            "agent": "reuseq",                   # Exploration agent (reuseq, random, model)
            "running_minutes": None,             # Will be calculated from task timeout
            "device_id": "emulator-5554",        # Target device
            "verbosity": 2,                      # Verbosity level (0-3)
            "fastbot_base_dir": None,            # Will be resolved at runtime
            "push_libraries": True,              # Whether to push native libraries
            "extract_strings": True,             # Whether to extract APK strings
            "cleanup_temp_files": True,          # Whether to cleanup temporary files
            "model_params": {                    # Model-specific parameters
                "learning_rate": 0.01,
                "exploration_rate": 0.1,
                "reward_decay": 0.9
            }
        }

        self.logger.info(f"Initialized FastBot tool with capabilities: {self.TOOL_SPEC.capabilities}")

    def configure_tool_specific(self, config: dict) -> None:
        """
        Configure FastBot-specific parameters.
        
        Supported configuration options:
        - throttle: Delay between events in milliseconds
        - agent: Exploration agent (reuseq, random, model)
        - running_minutes: Execution time limit in minutes
        - device_id: Target Android device identifier
        - verbosity: Output verbosity level (0-3)
        - push_libraries: Whether to push native libraries (default: True)
        - extract_strings: Whether to extract APK strings (default: True)
        - model_params: Dictionary with model-specific parameters
        
        Args:
            config: Configuration dictionary with FastBot parameters
        """
        # Update throttle delay
        if "throttle" in config:
            try:
                throttle = int(config["throttle"])
                if throttle >= 0:
                    self.config["throttle"] = throttle
                    self.logger.debug(f"Set FastBot throttle to: {throttle}ms")
                else:
                    self.logger.warning("Throttle must be non-negative")
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid throttle value: {config['throttle']}")

        # Update exploration agent
        if "agent" in config:
            agent = config["agent"]
            valid_agents = ["reuseq", "random", "model"]
            if agent in valid_agents:
                self.config["agent"] = agent
                self.logger.debug(f"Set FastBot agent to: {agent}")
            else:
                self.logger.warning(f"Invalid FastBot agent '{agent}', using default 'reuseq'")

        # Update running minutes if specified
        if "running_minutes" in config:
            try:
                minutes = int(config["running_minutes"])
                if minutes > 0:
                    self.config["running_minutes"] = minutes
                    self.logger.debug(f"Set FastBot running minutes to: {minutes}")
                else:
                    self.logger.warning("FastBot running minutes must be positive")
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid running_minutes value: {config['running_minutes']}")

        # Update device ID if specified
        if "device_id" in config:
            self.config["device_id"] = str(config["device_id"])
            self.logger.debug(f"Set FastBot device ID to: {self.config['device_id']}")

        # Update verbosity level
        if "verbosity" in config:
            try:
                verbosity = int(config["verbosity"])
                if 0 <= verbosity <= 3:
                    self.config["verbosity"] = verbosity
                    self.logger.debug(f"Set FastBot verbosity to: {verbosity}")
                else:
                    self.logger.warning("Verbosity must be between 0 and 3")
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid verbosity value: {config['verbosity']}")

        # Update boolean flags
        boolean_flags = ["push_libraries", "extract_strings", "cleanup_temp_files"]
        for flag in boolean_flags:
            if flag in config:
                self.config[flag] = bool(config[flag])
                self.logger.debug(f"Set FastBot {flag} to: {self.config[flag]}")

        # Update model parameters
        if "model_params" in config and isinstance(config["model_params"], dict):
            for param, value in config["model_params"].items():
                if param in self.config["model_params"]:
                    try:
                        self.config["model_params"][param] = float(value)
                        self.logger.debug(f"Set FastBot model {param} to: {value}")
                    except (ValueError, TypeError):
                        self.logger.warning(f"Invalid model parameter {param}: {value}")

    def execute_tool_specific_logic(self, task: Any, app: App) -> None:
        """
        Execute FastBot testing with configured parameters.
        
        ### Execution Workflow:
        1. Resolve FastBot installation directory and jar files
        2. Calculate execution timeout from task configuration
        3. Push FastBot jars and native libraries to Android device
        4. Extract APK strings for intelligent exploration (if enabled)
        5. Execute FastBot with specified agent and parameters
        6. Capture execution output for analysis
        7. Cleanup temporary files (if enabled)
        
        Args:
            task: Task configuration containing timeout and other parameters
            app: Application under test with package name and metadata
        """
        agent = self.config["agent"]
        device_id = self.config["device_id"]
        throttle = self.config["throttle"]
        
        self.logger.info(f"Executing FastBot tool with agent: {agent}")
        self.logger.debug(f"Target device: {device_id}, App: {app.package_name}, Throttle: {throttle}ms")

        # Resolve FastBot installation directory
        fastbot_base_dir = self._resolve_fastbot_directory()
        if not fastbot_base_dir:
            raise FileNotFoundError("FastBot installation not found. Please ensure FastBot is properly installed.")

        # Calculate timeout from task configuration
        timeout_in_seconds = getattr(task.config, 'timeout', 300)  # Default 5 minutes
        
        # Use configured running_minutes or calculate from timeout
        if self.config["running_minutes"] is not None:
            timeout_in_minutes = self.config["running_minutes"]
            timeout_in_seconds = timeout_in_minutes * 60  # Update seconds for command timeout
        else:
            timeout_in_minutes = max(1, int(timeout_in_seconds / 60))  # At least 1 minute

        self.logger.info(f"FastBot execution timeout: {timeout_in_minutes} minutes ({timeout_in_seconds} seconds)")

        # Execute FastBot testing workflow
        temp_files = []
        try:
            with open(task.result.trace_file, 'wb') as trace_file:
                # Push FastBot components to device
                self._deploy_fastbot_components(fastbot_base_dir, device_id, trace_file)
                
                # Extract APK strings for intelligent exploration
                if self.config["extract_strings"]:
                    strings_file = self._extract_apk_strings(app, fastbot_base_dir, device_id, trace_file)
                    if strings_file:
                        temp_files.append(strings_file)

                # Execute FastBot with configured parameters
                self._execute_fastbot_command(
                    app=app,
                    device_id=device_id,
                    agent=agent,
                    throttle=throttle,
                    timeout_minutes=timeout_in_minutes,
                    timeout_seconds=timeout_in_seconds,
                    trace_file=trace_file
                )

                self.logger.info("FastBot execution completed successfully")

        except Exception as e:
            self.logger.error(f"FastBot execution failed: {str(e)}")
            # Write error information to trace file
            with open(task.result.trace_file, 'ab') as trace_file:
                error_msg = f"FastBot execution error: {str(e)}\n"
                trace_file.write(error_msg.encode('utf-8'))
            raise
        finally:
            # Cleanup temporary files
            if self.config["cleanup_temp_files"]:
                self._cleanup_temp_files(temp_files)

    def _resolve_fastbot_directory(self) -> str:
        """
        Resolve the path to the FastBot installation directory.
        
        This method looks for FastBot in several possible locations:
        1. Configured path in self.config["fastbot_base_dir"]
        2. TOOLS_DIR environment variable + fastbot/
        3. Current directory + lib/fastbot/
        4. Default system locations
        
        Returns:
            Path to FastBot directory or None if not found
        """
        # Check configured path first
        if self.config.get("fastbot_base_dir") and os.path.isdir(self.config["fastbot_base_dir"]):
            return self.config["fastbot_base_dir"]

        # Common search paths for FastBot
        search_paths = [
            # Environment variable based path
            os.path.join(os.environ.get('TOOLS_DIR', ''), 'fastbot'),
            # Relative to current module
            os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'lib', 'fastbot'),
            # Standard installation paths
            '/opt/rv-android/lib/fastbot',
            './lib/fastbot',
            '../lib/fastbot'
        ]

        for path in search_paths:
            if path and os.path.isdir(path):
                # Verify required jars exist
                required_jars = ['monkeyq.jar', 'fastbot-thirdpart.jar', 'framework.jar']
                if all(os.path.isfile(os.path.join(path, jar)) for jar in required_jars):
                    self.logger.debug(f"Found FastBot installation at: {path}")
                    return path

        self.logger.error("FastBot installation not found in any of the expected locations")
        return None

    def _deploy_fastbot_components(self, fastbot_base_dir: str, device_id: str, trace_file) -> None:
        """
        Deploy FastBot jars and native libraries to the Android device.
        
        Args:
            fastbot_base_dir: FastBot installation directory
            device_id: Target device identifier
            trace_file: Output stream for command output
        """
        self.logger.info(f"Deploying FastBot components to device {device_id}")
        
        # Define jar files to push
        jar_files = {
            'monkeyq.jar': '/sdcard/monkeyq.jar',
            'fastbot-thirdpart.jar': '/sdcard/fastbot-thirdpart.jar',
            'framework.jar': '/sdcard/framework.jar'
        }
        
        # Push jar files
        for jar_name, device_path in jar_files.items():
            local_jar = os.path.join(fastbot_base_dir, jar_name)
            if os.path.isfile(local_jar):
                self._adb_push(local_jar, device_path, device_id, trace_file)
            else:
                raise FileNotFoundError(f"Required FastBot jar not found: {local_jar}")
        
        # Push native libraries if enabled
        if self.config["push_libraries"]:
            self._deploy_native_libraries(fastbot_base_dir, device_id, trace_file)

    def _deploy_native_libraries(self, fastbot_base_dir: str, device_id: str, trace_file) -> None:
        """
        Deploy FastBot native libraries to the Android device.
        
        Args:
            fastbot_base_dir: FastBot installation directory
            device_id: Target device identifier
            trace_file: Output stream for command output
        """
        libs_dir = os.path.join(fastbot_base_dir, "libs")
        if not os.path.isdir(libs_dir):
            self.logger.warning(f"Native libraries directory not found: {libs_dir}")
            return
        
        # Define native libraries for different architectures
        architectures = ["arm64-v8a", "armeabi-v7a", "x86", "x86_64"]
        
        for arch in architectures:
            lib_file = os.path.join(libs_dir, arch, "libfastbot_native.so")
            if os.path.isfile(lib_file):
                device_lib_path = f"/data/local/tmp/{arch}/libfastbot_native.so"
                self._adb_push(lib_file, device_lib_path, device_id, trace_file)
            else:
                self.logger.debug(f"Native library not found for {arch}: {lib_file}")

    def _extract_apk_strings(self, app: App, fastbot_base_dir: str, device_id: str, trace_file) -> str:
        """
        Extract APK strings for intelligent exploration.
        
        Args:
            app: Application under test
            fastbot_base_dir: FastBot installation directory
            device_id: Target device identifier
            trace_file: Output stream for command output
            
        Returns:
            Path to temporary strings file or None if extraction failed
        """
        strings_file = os.path.join(fastbot_base_dir, "max.valid.strings")
        
        try:
            self.logger.debug(f"Extracting APK strings from: {app.path}")
            
            # Extract strings using aapt2
            with open(strings_file, "wb") as strings_output:
                aapt_cmd = Command("aapt2", ["dump", "strings", app.path])
                aapt_cmd.invoke(stdout=strings_output)
            
            # Push strings file to device
            self._adb_push(strings_file, "/sdcard/max.valid.strings", device_id, trace_file)
            
            self.logger.debug("APK strings extracted and pushed to device")
            return strings_file
            
        except Exception as e:
            self.logger.warning(f"Failed to extract APK strings: {str(e)}")
            return None

    def _execute_fastbot_command(self, app: App, device_id: str, agent: str, throttle: int,
                                timeout_minutes: int, timeout_seconds: int, trace_file) -> None:
        """
        Execute the FastBot testing command on the device.
        
        Args:
            app: Application under test
            device_id: Target device identifier
            agent: FastBot exploration agent
            throttle: Delay between events
            timeout_minutes: Execution timeout in minutes
            timeout_seconds: Command timeout in seconds
            trace_file: Output stream for command output
        """
        self.logger.info(f"Starting FastBot execution for {app.package_name} with {agent} agent")
        
        # Build verbosity flags
        verbosity_flags = ["-v"] * self.config["verbosity"]
        
        # Construct FastBot command
        fastbot_cmd = Command('adb', [
            '-s', device_id,
            'shell',
            'CLASSPATH=/sdcard/monkeyq.jar:/sdcard/framework.jar:/sdcard/fastbot-thirdpart.jar',
            'exec',
            'app_process',
            '/system/bin',
            'com.android.commands.monkey.Monkey',
            '-p', app.package_name,
            '--agent', agent,
            '--running-minutes', str(timeout_minutes),
            '--throttle', str(throttle)
        ] + verbosity_flags, timeout_seconds)

        # Build command string for logging
        cmd_str = f"{fastbot_cmd.command} {' '.join(fastbot_cmd.args)}"
        self.logger.debug(f"FastBot command: {cmd_str}")
        
        try:
            # Execute FastBot command
            fastbot_cmd.invoke(stdout=trace_file)
            self.logger.info(f"FastBot command completed for {app.package_name}")
            
        except Exception as e:
            self.logger.error(f"FastBot command execution failed: {str(e)}")
            raise

    def _adb_push(self, local_file: str, device_path: str, device_id: str, trace_file) -> None:
        """
        Push a file to the Android device.
        
        Args:
            local_file: Local file path to push
            device_path: Destination path on device
            device_id: Target device identifier
            trace_file: Output stream for command output
        """
        self.logger.debug(f"Pushing file to device {device_id}: {local_file} -> {device_path}")
        
        push_cmd = Command('adb', [
            '-s', device_id,
            'push', '-a', '-p',
            local_file,
            device_path
        ])
        
        try:
            push_cmd.invoke(stdout=trace_file)
            self.logger.debug(f"Successfully pushed: {os.path.basename(local_file)}")
        except Exception as e:
            self.logger.error(f"Failed to push {local_file} to device: {str(e)}")
            raise

    def _cleanup_temp_files(self, temp_files: list) -> None:
        """
        Cleanup temporary files created during execution.
        
        Args:
            temp_files: List of temporary file paths to remove
        """
        if not temp_files:
            return
            
        self.logger.debug(f"Cleaning up {len(temp_files)} temporary files")
        
        for file_path in temp_files:
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    self.logger.debug(f"Removed temporary file: {file_path}")
            except Exception as e:
                self.logger.warning(f"Failed to remove temporary file {file_path}: {str(e)}")

    def get_supported_agents(self) -> list:
        """
        Get list of supported FastBot exploration agents.
        
        Returns:
            List of supported agent names
        """
        return ["reuseq", "random", "model"]

    def get_tool_info(self) -> dict:
        """
        Get comprehensive FastBot tool information.
        
        Returns:
            Dictionary with tool information, capabilities, and current configuration
        """
        info = super().get_tool_info()
        info.update({
            "tool_spec": self.TOOL_SPEC.to_dict(),
            "supported_agents": self.get_supported_agents(),
            "current_agent": self.config["agent"],
            "current_throttle": self.config["throttle"],
            "version": self.TOOL_SPEC.version,
            "category": self.TOOL_SPEC.category.value
        })
        return info