"""
Humanoid human-like testing tool implementation.

This module provides integration with the Humanoid Android testing framework,
enabling human-like testing with computer vision and natural language processing.
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


class HumanoidTool(AbstractTool):
    """
    Humanoid human-like testing tool with computer vision and NLP capabilities.

    ### Architectural Decisions:
    - Inherits directly from AbstractTool for simplified architecture
    - Implements human-like testing using computer vision and natural language processing
    - Provides intelligent interaction based on visual understanding and context
    - Uses script-based execution model for flexible testing scenarios
    - Supports multiple interaction modes and configuration options
    - Integrates with rv-android-core infrastructure for error handling and logging

    ### Role in the System:
    - Serves as a human-like testing tool for natural Android app interaction
    - Provides computer vision-based UI understanding and interaction
    - Enables context-aware testing using natural language processing
    - Supports both JCA cryptography detection and generic monitored operations testing
    - Facilitates advanced testing through human-like behavior simulation

    ### Key Features:
    - Computer vision-based UI element recognition and interaction
    - Natural language processing for context understanding
    - Human-like interaction patterns and timing
    - Script-based execution for complex testing scenarios
    - Integration with Android Debug Bridge (ADB) for device communication

    ### Tool Variants:
    Humanoid supports different interaction modes as variants:
    - visual: Visual-based interaction using computer vision
    - nlp: NLP-enhanced interaction with context understanding
    - hybrid: Combined visual and NLP capabilities
    """

    # Simplified tool specification
    TOOL_SPEC = ToolSpec.create_builtin_spec(
        name="humanoid",
        description="Humanoid human-like testing tool with computer vision and NLP capabilities",
        url="https://github.com/yzygitzh/Humanoid",
        version="1.0.0",
        process_pattern="humanoid"
    )

    # Available interaction modes
    AVAILABLE_MODES = [
        'visual', 'nlp', 'hybrid', 'basic'
    ]

    def __init__(self, name: str = None, description: str = None, process_pattern: str = None):
        """
        Initialize the Humanoid tool with rv-android-core infrastructure.
        """
        super().__init__(
            name=name or self.TOOL_SPEC.name,
            description=description or self.TOOL_SPEC.description,
            process_pattern=process_pattern or self.TOOL_SPEC.process_pattern
        )

        # Initialize rv-android-core infrastructure components
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_tools.builtin.humanoid",
            {CONTEXT_COMPONENT: "HumanoidTool"}
        )

        # Default Humanoid configuration
        self.config = {
            "interaction_mode": "hybrid",    # Interaction mode
            "device_serial": None,           # Device serial number
            "script_path": None,             # Path to Humanoid script
            "timeout": 1800,                 # Execution timeout in seconds (30 minutes)
            "debug_mode": False,             # Enable debug mode
            "visual_threshold": 0.8,         # Visual recognition threshold
            "nlp_model": "default",          # NLP model to use
            "interaction_delay": 2.0,        # Delay between interactions (seconds)
            "screenshot_interval": 1.0,      # Screenshot capture interval (seconds)
            "max_iterations": 1000,          # Maximum test iterations
            "enable_learning": True,         # Enable learning from interactions
            "context_window": 5,             # Context window for NLP
            "vision_model": "default"        # Computer vision model
        }

        self.logger.info("Initialized Humanoid tool for human-like exploration")

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure Humanoid-specific parameters.

        Supported configuration options:
        - interaction_mode: Interaction mode (visual, nlp, hybrid, basic)
        - device_serial: Device serial number
        - script_path: Path to Humanoid script
        - timeout: Execution timeout in seconds
        - debug_mode: Enable debug mode
        - visual_threshold: Visual recognition threshold
        - nlp_model: NLP model to use
        - interaction_delay: Delay between interactions in seconds
        - screenshot_interval: Screenshot capture interval in seconds
        - max_iterations: Maximum test iterations
        - enable_learning: Enable learning from interactions
        - context_window: Context window for NLP
        - vision_model: Computer vision model

        Args:
            config: Configuration dictionary with Humanoid parameters
        """
        if not config:
            return

        # Update interaction mode
        if 'interaction_mode' in config:
            mode = config['interaction_mode']
            if mode not in self.AVAILABLE_MODES:
                self.logger.warning(f"Invalid interaction mode '{mode}'. Using default 'hybrid'")
                self.logger.warning(f"Available modes: {self.AVAILABLE_MODES}")
            else:
                self.config['interaction_mode'] = mode
                self.logger.debug(f"Set Humanoid interaction mode to: {mode}")

        # Update device serial
        if 'device_serial' in config:
            self.config['device_serial'] = config['device_serial']
            self.logger.debug(f"Set Humanoid device serial to: {config['device_serial']}")

        # Update script path
        if 'script_path' in config:
            self.config['script_path'] = config['script_path']
            self.logger.debug(f"Set Humanoid script path to: {config['script_path']}")

        # Update timeout
        if 'timeout' in config:
            try:
                timeout = int(config['timeout'])
                if timeout > 0:
                    self.config['timeout'] = timeout
                    self.logger.debug(f"Set Humanoid timeout to: {timeout}s")
                else:
                    self.logger.warning("Timeout must be positive")
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid timeout value: {config['timeout']}")

        # Update visual threshold
        if 'visual_threshold' in config:
            try:
                threshold = float(config['visual_threshold'])
                if 0.0 <= threshold <= 1.0:
                    self.config['visual_threshold'] = threshold
                    self.logger.debug(f"Set Humanoid visual threshold to: {threshold}")
                else:
                    self.logger.warning("Visual threshold must be between 0.0 and 1.0")
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid visual_threshold value: {config['visual_threshold']}")

        # Update interaction delay
        if 'interaction_delay' in config:
            try:
                delay = float(config['interaction_delay'])
                if delay >= 0.0:
                    self.config['interaction_delay'] = delay
                    self.logger.debug(f"Set Humanoid interaction delay to: {delay}s")
                else:
                    self.logger.warning("Interaction delay must be non-negative")
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid interaction_delay value: {config['interaction_delay']}")

        # Update screenshot interval
        if 'screenshot_interval' in config:
            try:
                interval = float(config['screenshot_interval'])
                if interval > 0.0:
                    self.config['screenshot_interval'] = interval
                    self.logger.debug(f"Set Humanoid screenshot interval to: {interval}s")
                else:
                    self.logger.warning("Screenshot interval must be positive")
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid screenshot_interval value: {config['screenshot_interval']}")

        # Update max iterations
        if 'max_iterations' in config:
            try:
                iterations = int(config['max_iterations'])
                if iterations > 0:
                    self.config['max_iterations'] = iterations
                    self.logger.debug(f"Set Humanoid max iterations to: {iterations}")
                else:
                    self.logger.warning("Max iterations must be positive")
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid max_iterations value: {config['max_iterations']}")

        # Update context window
        if 'context_window' in config:
            try:
                window = int(config['context_window'])
                if window > 0:
                    self.config['context_window'] = window
                    self.logger.debug(f"Set Humanoid context window to: {window}")
                else:
                    self.logger.warning("Context window must be positive")
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid context_window value: {config['context_window']}")

        # Update boolean flags
        if 'debug_mode' in config:
            self.config['debug_mode'] = bool(config['debug_mode'])
            self.logger.debug(f"Set Humanoid debug mode to: {self.config['debug_mode']}")

        if 'enable_learning' in config:
            self.config['enable_learning'] = bool(config['enable_learning'])
            self.logger.debug(f"Set Humanoid enable learning to: {self.config['enable_learning']}")

        # Update model configurations
        model_params = ['nlp_model', 'vision_model']
        for param in model_params:
            if param in config:
                self.config[param] = str(config[param])
                self.logger.debug(f"Set Humanoid {param} to: {config[param]}")

    @ErrorHandler.handle_errors(
        component="HumanoidTool",
        phase="execute_tool_specific_logic"
    )
    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
        """
        Execute Humanoid testing with configured parameters.

        ### Execution Workflow:
        1. Resolve Humanoid script and model files
        2. Prepare computer vision and NLP models
        3. Execute Humanoid with specified interaction mode
        4. Capture execution output and interaction logs
        5. Process results and learning data

        Args:
            task: Task configuration containing timeout and other parameters
            app: Application under test with package name and metadata
        """
        self.logger.info(f"Executing Humanoid tool for {app.package_name}")
        self.logger.debug(f"Mode: {self.config['interaction_mode']}, Max iterations: {self.config['max_iterations']}")

        # Get timeout from task configuration
        timeout_in_seconds = getattr(task.config, 'timeout', self.config['timeout'])
        
        self.logger.info(f"Humanoid execution timeout: {timeout_in_seconds} seconds")

        # Create output directory for Humanoid results
        output_dir = os.path.join(os.path.dirname(task.result.trace_file), "humanoid_output")
        os.makedirs(output_dir, exist_ok=True)

        # Resolve Humanoid script
        script_path = self._resolve_humanoid_script()

        # Build Humanoid command
        humanoid_cmd = self._build_humanoid_command(app, script_path, output_dir, timeout_in_seconds)
        
        # Build command string for logging
        cmd_str = f"{humanoid_cmd.command} {' '.join(humanoid_cmd.args)}"
        self.logger.debug(f"Humanoid command: {cmd_str}")

        # Execute Humanoid testing with centralized error handling
        try:
            self.logger.info(f"Starting Humanoid execution for {app.package_name}")
            
            # Execute command with output redirection (binary mode for command output)
            with open(task.result.trace_file, 'wb') as trace_file:
                # Use centralized command execution with error handling
                # Redirect both stdout and stderr to trace file to prevent console flooding
                result = self._execute_and_check_command(humanoid_cmd, stdout=trace_file, stderr=trace_file)
            
            # Append success information to trace file (text mode for metadata)
            # with open(task.result.trace_file, 'a', encoding='utf-8') as trace_file:
            #     success_info = f"\n--- Humanoid Execution Completed ---\n"
            #     success_info += f"Interaction mode: {self.config['interaction_mode']}\n"
            #     success_info += f"Max iterations: {self.config['max_iterations']}\n"
            #     success_info += f"Visual threshold: {self.config['visual_threshold']}\n"
            #     success_info += f"NLP model: {self.config['nlp_model']}\n"
            #     success_info += f"Output directory: {output_dir}\n"
            #     success_info += f"Command: {cmd_str}\n"
            #     trace_file.write(success_info)
            
            self.logger.info("Humanoid execution completed successfully")
            
        except Exception as e:
            self.logger.error(f"Humanoid execution failed: {str(e)}")
            raise

    def _resolve_humanoid_script(self) -> str:
        """
        Resolve the path to the Humanoid script.

        Returns:
            Path to Humanoid script

        Raises:
            FileNotFoundError: If Humanoid script is not found
        """
        # Check configured path first
        if self.config.get("script_path") and os.path.isfile(self.config["script_path"]):
            return self.config["script_path"]

        # Common search paths for Humanoid script
        search_paths = [
            # Environment variable based path
            os.path.join(os.environ.get('TOOLS_DIR', ''), 'humanoid', 'run_humanoid.sh'),
            # Relative to current module
            os.path.join(os.path.dirname(__file__), 'run_humanoid.sh'),
            # Standard installation paths
            '/opt/rv-android/tools/humanoid/run_humanoid.sh',
            './tools/humanoid/run_humanoid.sh',
            '../tools/humanoid/run_humanoid.sh'
        ]

        for path in search_paths:
            if path and os.path.isfile(path):
                self.logger.debug(f"Found Humanoid script at: {path}")
                return path

        raise FileNotFoundError("Humanoid script not found. Please ensure Humanoid is properly installed.")

    def _build_humanoid_command(self, app: App, script_path: str, output_dir: str, timeout_seconds: int) -> Command:
        """
        Build the Humanoid command with configured parameters.

        Args:
            app: Application under test
            script_path: Path to Humanoid script
            output_dir: Output directory for Humanoid results
            timeout_seconds: Command execution timeout

        Returns:
            Configured Command object for Humanoid execution
        """
        # Start building command arguments
        cmd_args = [
            script_path,
            "--apk", app.apk_path,
            "--package", app.package_name,
            "--output", output_dir,
            "--mode", self.config["interaction_mode"],
            "--max-iterations", str(self.config["max_iterations"]),
            "--timeout", str(self.config["timeout"])
        ]

        # Add device serial if specified
        if self.config["device_serial"]:
            cmd_args.extend(["--device", self.config["device_serial"]])

        # Add visual parameters
        cmd_args.extend([
            "--visual-threshold", str(self.config["visual_threshold"]),
            "--vision-model", self.config["vision_model"]
        ])

        # Add NLP parameters
        cmd_args.extend([
            "--nlp-model", self.config["nlp_model"],
            "--context-window", str(self.config["context_window"])
        ])

        # Add timing parameters
        cmd_args.extend([
            "--interaction-delay", str(self.config["interaction_delay"]),
            "--screenshot-interval", str(self.config["screenshot_interval"])
        ])

        # Add debug mode if enabled
        if self.config["debug_mode"]:
            cmd_args.append("--debug")

        # Add learning flag if enabled
        if self.config["enable_learning"]:
            cmd_args.append("--enable-learning")

        return Command("bash", cmd_args, timeout_seconds)

    def get_available_modes(self) -> List[str]:
        """
        Get list of available interaction modes.

        Returns:
            List of available mode names
        """
        return self.AVAILABLE_MODES.copy()

    def get_tool_info(self) -> dict:
        """
        Get comprehensive Humanoid tool information.

        Returns:
            Dictionary with tool information and current configuration
        """
        info = super().get_tool_info()
        info.update({
            "tool_spec": self.TOOL_SPEC.to_dict(),
            "available_modes": self.get_available_modes(),
            "current_mode": self.config["interaction_mode"],
            "current_max_iterations": self.config["max_iterations"],
            "visual_threshold": self.config["visual_threshold"],
            "nlp_model": self.config["nlp_model"],
            "vision_model": self.config["vision_model"],
            "enable_learning": self.config["enable_learning"],
            "version": self.TOOL_SPEC.version,
            "url": self.TOOL_SPEC.url
        })
        return info


# Function to register Humanoid variants
def register_humanoid_variants(registry):
    """
    Register Humanoid variants in the tool registry.
    
    Args:
        registry: ToolRegistry instance
    """
    # Register interaction mode variants
    variants = {
        "visual": {"interaction_mode": "visual", "visual_threshold": 0.9},
        "nlp": {"interaction_mode": "nlp", "context_window": 10},
        "hybrid": {"interaction_mode": "hybrid", "visual_threshold": 0.8, "context_window": 5},
        "basic": {"interaction_mode": "basic", "enable_learning": False}
    }
    
    for variant_name, config in variants.items():
        registry.register_variant("humanoid", variant_name, config)