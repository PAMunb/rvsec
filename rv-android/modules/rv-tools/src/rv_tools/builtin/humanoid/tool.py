"""
Humanoid tool implementation for human-like monitored operations testing.

This module provides integration with the Humanoid Android testing framework,
enabling human-like test input generation through computer vision and natural language processing.
"""

import os
from typing import Dict, Any, List

from rv_android_core.app import App
from rv_android_core.commands.command import Command
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.tools.configurable_tool import ConfigurableTool
from rv_android_core.tools.tool_spec import ToolSpec, ToolCategory


class HumanoidTool(ConfigurableTool):
    """
    Humanoid human-like testing tool for monitored operations testing.

    ### Architectural Decisions:
    - Extends ConfigurableTool to leverage standardized configuration management
    - Implements human-like interaction strategies using computer vision and natural language
    - Provides comprehensive GUI exploration with human behavior modeling capabilities
    - Uses DroidBot framework integration for efficient execution and trace generation
    - Supports configurable policies for different exploration strategies
    - Integrates with rv-android-core infrastructure for error handling and logging

    ### Role in the System:
    - Serves as a human-like testing tool for monitored operations using computer vision
    - Provides natural language understanding for intelligent interaction with UI elements
    - Enables human behavior modeling for realistic application testing scenarios
    - Supports both guided and autonomous exploration with configurable policy strategies
    - Facilitates computer vision-based UI element recognition and interaction
    - Generates detailed trace files for comprehensive result analysis and debugging

    ### Key Considerations:
    - Uses computer vision techniques for UI element detection and classification
    - Implements natural language processing for understanding UI context and content
    - Supports human-like interaction patterns including gestures and navigation flows
    - Provides configurable exploration policies for different testing objectives
    - Handles both emulator and real device execution environments
    - Integrates with DroidBot framework for standardized execution and tracing

    ### Integration Strategy:
    - Compatible with experiment task execution system for automated workflows
    - Supports configuration inheritance from experiment and variant specifications
    - Enables result collection and analysis through standardized trace file format
    - Provides clear extension points for custom exploration policies and behaviors
    - Facilitates integration with coverage analysis and UI pattern recognition systems
    - Supports plugin-based architecture for external tool ecosystem integration

    ### Performance and Scalability:
    - Optimized for human-like interaction speed with configurable timing parameters
    - Supports configurable timeout mechanisms to prevent resource exhaustion
    - Enables parallel execution across multiple device instances and applications
    - Provides intelligent exploration strategies to minimize redundant actions
    - Scales effectively for large-scale experiment execution scenarios
    - Adaptable to different APK complexity and UI design patterns

    ### Human-Like Testing Features:
    - Computer vision-based element detection and interaction
    - Natural language understanding for UI content analysis
    - Human behavior modeling for realistic interaction patterns
    - Gesture recognition and sophisticated touch interaction simulation
    - Context-aware navigation and exploration strategies
    - Adaptive learning from previous interaction experiences
    """

    # Humanoid tool specification with comprehensive metadata
    TOOL_SPEC = ToolSpec.create_builtin_spec(
        name="humanoid",
        description="Humanoid human-like testing tool using computer vision and natural language processing",
        category=ToolCategory.AI_GUIDED,
        version="1.0.0",
        process_pattern="humanoid",
        capabilities=[
            "human_like_testing",
            "computer_vision",
            "natural_language_understanding",
            "ui_element_recognition",
            "gesture_simulation",
            "context_aware_navigation",
            "behavior_modeling",
            "adaptive_exploration",
            "trace_generation",
            "monitored_operations_testing"
        ]
    )

    def __init__(self):
        """
        Initialize the Humanoid tool with default configuration.
        
        Sets up tool metadata, default parameters, and establishes
        integration with rv-android-core infrastructure.
        """
        super().__init__(
            name=self.TOOL_SPEC.name,
            description=self.TOOL_SPEC.description,
            process_pattern=self.TOOL_SPEC.process_pattern
        )

        # Initialize logging and error handling
        self.error_handler = ErrorHandler.get_instance()
        self.logging_manager = LoggingManager.get_instance()

        # Default tool configuration
        self.default_config = {
            "humanoid_url": "127.0.0.1:50405",
            "policy": "dfs_greedy",
            "timeout": 600,  # 10 minutes
            "device_id": "emulator-5554",
            "is_emulator": True,
            "vision_enabled": True,
            "nlp_enabled": True,
            "behavior_model": "human",
            "interaction_delay": 1.0,  # Seconds between interactions
            "gesture_recognition": True,
            "context_awareness": True,
            "adaptive_learning": True,
            "output_dir": None,
            "debug_mode": False,
            "trace_level": "detailed"
        }

        # Merge default configuration with current tool configuration
        self.tool_config = self.default_config.copy()

        self.logger.info("Humanoid tool initialized successfully")

    def configure_tool_specific(self, config: Dict[str, Any]) -> None:
        """
        Configure Humanoid-specific parameters and validate settings.

        Args:
            config: Configuration dictionary with tool-specific parameters

        Raises:
            ValueError: If configuration parameters are invalid
        """
        self.logger.debug("Configuring Humanoid-specific parameters")

        try:
            # Humanoid URL configuration
            if 'humanoid_url' in config:
                humanoid_url = config['humanoid_url']
                if not isinstance(humanoid_url, str) or not humanoid_url.strip():
                    raise ValueError("humanoid_url must be a non-empty string")
                self.tool_config['humanoid_url'] = humanoid_url.strip()

            # Policy configuration
            if 'policy' in config:
                policy = config['policy']
                valid_policies = [
                    'dfs_naive', 'dfs_greedy', 'bfs_naive', 'bfs_greedy',
                    'random', 'human_like', 'vision_guided', 'context_aware'
                ]
                if policy not in valid_policies:
                    raise ValueError(f"policy must be one of: {valid_policies}")
                self.tool_config['policy'] = policy

            # Timeout configuration
            if 'timeout' in config:
                timeout = config['timeout']
                if not isinstance(timeout, int) or timeout < 1:
                    raise ValueError("timeout must be a positive integer")
                self.tool_config['timeout'] = timeout

            # Device configuration
            if 'device_id' in config:
                self.tool_config['device_id'] = str(config['device_id'])

            # Interaction delay configuration
            if 'interaction_delay' in config:
                delay = config['interaction_delay']
                if not isinstance(delay, (int, float)) or delay < 0:
                    raise ValueError("interaction_delay must be a non-negative number")
                self.tool_config['interaction_delay'] = delay

            # Behavior model configuration
            if 'behavior_model' in config:
                model = config['behavior_model']
                valid_models = ['human', 'expert', 'novice', 'exploratory', 'systematic']
                if model not in valid_models:
                    raise ValueError(f"behavior_model must be one of: {valid_models}")
                self.tool_config['behavior_model'] = model

            # Trace level configuration
            if 'trace_level' in config:
                level = config['trace_level']
                valid_levels = ['minimal', 'standard', 'detailed', 'comprehensive']
                if level not in valid_levels:
                    raise ValueError(f"trace_level must be one of: {valid_levels}")
                self.tool_config['trace_level'] = level

            # Output directory configuration
            if 'output_dir' in config:
                self.tool_config['output_dir'] = str(config['output_dir'])

            # Boolean flags
            boolean_flags = [
                'is_emulator', 'vision_enabled', 'nlp_enabled', 'gesture_recognition',
                'context_awareness', 'adaptive_learning', 'debug_mode'
            ]
            
            for flag in boolean_flags:
                if flag in config:
                    self.tool_config[flag] = bool(config[flag])

            self.logger.info("Humanoid tool configuration completed successfully")

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "configure_tool_specific",
                    "tool": "humanoid",
                    "component": "HumanoidTool"
                }
            )
            raise

    def execute_tool_specific_logic(self, task: Any, app: App) -> None:
        """
        Execute Humanoid-specific testing logic through DroidBot integration.
        
        This method implements the core Humanoid execution workflow including
        environment validation, command preparation, and execution with comprehensive
        error handling and trace generation.
        
        Args:
            task: Task configuration containing timeout and other parameters
            app: Application under test with path and metadata
        """
        try:
            self.logger.info(f"Executing Humanoid tool for app: {app.name}")
            self.logger.debug(f"Humanoid URL: {self.tool_config['humanoid_url']}")
            self.logger.debug(f"Policy: {self.tool_config['policy']}")
            self.logger.debug(f"Behavior model: {self.tool_config['behavior_model']}")

            # Validate execution environment
            if not self.validate_execution_environment(app):
                raise RuntimeError("Humanoid execution environment validation failed")

            # Get task configuration timeout
            task_config = {"timeout": getattr(task.config, 'timeout', self.tool_config['timeout'])}
            
            # Determine output file from task
            output_file = getattr(task.result, 'trace_file', None)
            if not output_file:
                raise ValueError("No output trace file specified in task result")

            # Create execution command
            command = self.get_execution_command(app, output_file, task_config)
            
            self.logger.info(f"Starting Humanoid execution with timeout: {task_config['timeout']} seconds")
            
            # Execute the command and capture output
            with open(output_file, 'wb') as trace_file:
                result = command.invoke(stdout=trace_file)
                
                # Process execution result
                execution_result = self.process_execution_result(result, app, output_file)
                
                # Log execution summary
                if execution_result.get('success', False):
                    self.logger.info(f"Humanoid execution completed successfully for app: {app.name}")
                    self.logger.info(f"Human-like interactions detected: {execution_result.get('human_like_interactions', 0)}")
                    self.logger.info(f"Monitored operations detected: {execution_result.get('monitored_operations_detected', 0)}")
                else:
                    self.logger.warning(f"Humanoid execution failed for app: {app.name}")
                    if execution_result.get('timeout_occurred', False):
                        self.logger.warning("Execution terminated due to timeout")
                    
                    error_details = execution_result.get('error_details', '')
                    if error_details:
                        self.logger.error(f"Error details: {error_details}")

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "execute_tool_specific_logic",
                    "app_name": app.name,
                    "tool": "humanoid",
                    "component": "HumanoidTool"
                }
            )
            raise

    def build_command_args(self, app: App, output_file: str, task_config: Dict[str, Any]) -> List[str]:
        """
        Build command arguments for Humanoid execution through DroidBot.

        Args:
            app: Application instance containing APK information
            output_file: Path to output trace file
            task_config: Task-specific configuration parameters

        Returns:
            List of command arguments for tool execution
        """
        try:
            self.logger.debug(f"Building Humanoid command arguments for app: {app.name}")

            # Base DroidBot arguments with Humanoid integration
            args = [
                "-d", self.tool_config['device_id'],
                "-a", app.path,
                "-humanoid", self.tool_config['humanoid_url'],
                "-policy", self.tool_config['policy']
            ]

            # Timeout configuration
            timeout_seconds = task_config.get('timeout', self.tool_config['timeout'])
            args.extend(["-timeout", str(timeout_seconds)])

            # Output directory configuration
            if self.tool_config.get('output_dir'):
                args.extend(["-o", self.tool_config['output_dir']])

            # Emulator flag
            if self.tool_config['is_emulator']:
                args.append("-is_emulator")

            # Debug mode
            if self.tool_config['debug_mode']:
                args.append("-debug")

            # Add Humanoid-specific parameters as environment variables or additional args
            # Note: Some parameters may need to be passed through environment variables
            # depending on Humanoid's implementation

            self.logger.debug(f"Humanoid command arguments: {args}")
            return args

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "build_command_args",
                    "app_name": app.name,
                    "tool": "humanoid",
                    "component": "HumanoidTool"
                }
            )
            raise

    def validate_execution_environment(self, app: App) -> bool:
        """
        Validate that the execution environment is properly configured for Humanoid.

        Args:
            app: Application instance to validate against

        Returns:
            True if environment is valid, False otherwise
        """
        try:
            self.logger.debug("Validating Humanoid execution environment")

            # Check if DroidBot is available (required for Humanoid integration)
            try:
                droidbot_check = Command("droidbot", ["--help"], timeout=10)
                result = droidbot_check.invoke()
                if result.returncode != 0:
                    self.logger.error("DroidBot is not available (required for Humanoid)")
                    return False
            except Exception as e:
                self.logger.error(f"DroidBot validation failed: {str(e)}")
                return False

            # Check if ADB is available
            try:
                adb_check = Command("adb", ["devices"], timeout=10)
                result = adb_check.invoke()
                if result.returncode != 0:
                    self.logger.error("ADB is not available or not responding")
                    return False
            except Exception as e:
                self.logger.error(f"ADB validation failed: {str(e)}")
                return False

            # Validate APK file
            if not os.path.exists(app.path):
                self.logger.error(f"APK file not found: {app.path}")
                return False

            # Check device connectivity
            device_id = self.tool_config['device_id']
            try:
                device_check = Command("adb", ["-s", device_id, "shell", "echo", "test"], timeout=10)
                result = device_check.invoke()
                if result.returncode != 0:
                    self.logger.error(f"Device not accessible: {device_id}")
                    return False
            except Exception as e:
                self.logger.error(f"Device connectivity check failed: {str(e)}")
                return False

            # Validate Humanoid URL accessibility (basic check)
            humanoid_url = self.tool_config['humanoid_url']
            if not humanoid_url or ':' not in humanoid_url:
                self.logger.error(f"Invalid Humanoid URL format: {humanoid_url}")
                return False

            self.logger.info("Humanoid execution environment validation successful")
            return True

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "validate_execution_environment",
                    "app_name": app.name,
                    "tool": "humanoid",
                    "component": "HumanoidTool"
                }
            )
            return False

    def get_execution_command(self, app: App, output_file: str, task_config: Dict[str, Any]) -> Command:
        """
        Create the execution command for Humanoid tool.

        Args:
            app: Application instance
            output_file: Path to output trace file
            task_config: Task-specific configuration

        Returns:
            Configured Command instance for execution
        """
        try:
            # Build command arguments
            args = self.build_command_args(app, output_file, task_config)
            
            # Calculate timeout with buffer
            timeout_seconds = task_config.get('timeout', self.tool_config['timeout'])
            execution_timeout = timeout_seconds + 30  # Add 30 second buffer

            # Create command with comprehensive configuration
            command = Command(
                executable="droidbot",
                args=args,
                timeout=execution_timeout
            )

            self.logger.info(f"Humanoid execution command created for app: {app.name}")
            return command

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "get_execution_command",
                    "app_name": app.name,
                    "tool": "humanoid",
                    "component": "HumanoidTool"
                }
            )
            raise

    def process_execution_result(self, result, app: App, output_file: str) -> Dict[str, Any]:
        """
        Process the execution result and extract relevant metrics.

        Args:
            result: Command execution result
            app: Application instance
            output_file: Path to output trace file

        Returns:
            Dictionary containing execution metrics and status information
        """
        try:
            self.logger.debug(f"Processing Humanoid execution result for app: {app.name}")

            # Base result information
            execution_result = {
                "tool": "humanoid",
                "app_name": app.name,
                "execution_time": getattr(result, 'execution_time', 0),
                "return_code": result.returncode,
                "success": result.returncode == 0,
                "output_file": output_file,
                "trace_generated": os.path.exists(output_file) if output_file else False
            }

            # Add tool-specific metrics
            if result.returncode == 0:
                execution_result.update({
                    "exploration_completed": True,
                    "timeout_occurred": False,
                    "policy_used": self.tool_config['policy'],
                    "behavior_model": self.tool_config['behavior_model'],
                    "human_like_interactions": self._analyze_trace_for_human_interactions(output_file),
                    "monitored_operations_detected": self._analyze_trace_for_monitored_operations(output_file),
                    "vision_enabled": self.tool_config['vision_enabled'],
                    "nlp_enabled": self.tool_config['nlp_enabled']
                })
            else:
                execution_result.update({
                    "exploration_completed": False,
                    "timeout_occurred": result.returncode == 124,  # Standard timeout return code
                    "error_details": getattr(result, 'stderr', ''),
                    "policy_used": self.tool_config['policy'],
                    "behavior_model": self.tool_config['behavior_model'],
                    "human_like_interactions": 0,
                    "monitored_operations_detected": 0
                })

            # Extract additional metrics from trace file
            if output_file and os.path.exists(output_file):
                execution_result.update(self._extract_trace_metrics(output_file))

            self.logger.info(f"Humanoid execution result processed for app: {app.name}")
            return execution_result

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "process_execution_result",
                    "app_name": app.name,
                    "tool": "humanoid",
                    "component": "HumanoidTool"
                }
            )
            
            # Return basic error result
            return {
                "tool": "humanoid",
                "app_name": app.name,
                "success": False,
                "error": f"Result processing failed: {str(e)}"
            }

    def _analyze_trace_for_human_interactions(self, trace_file: str) -> int:
        """
        Analyze trace file for human-like interaction patterns.

        Args:
            trace_file: Path to the trace file

        Returns:
            Number of human-like interactions detected
        """
        try:
            if not os.path.exists(trace_file):
                return 0

            # Simple analysis - count lines that might indicate human-like interactions
            human_interactions = 0
            with open(trace_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    # Look for patterns that indicate human-like behavior
                    if any(keyword in line.lower() for keyword in [
                        'gesture', 'swipe', 'scroll', 'long_press', 'double_tap',
                        'human', 'vision', 'nlp', 'context', 'behavior'
                    ]):
                        human_interactions += 1

            return human_interactions

        except Exception as e:
            self.logger.warning(f"Failed to analyze trace file for human interactions: {str(e)}")
            return 0

    def _analyze_trace_for_monitored_operations(self, trace_file: str) -> int:
        """
        Analyze trace file for monitored operations occurrences.

        Args:
            trace_file: Path to the trace file

        Returns:
            Number of monitored operations detected
        """
        try:
            if not os.path.exists(trace_file):
                return 0

            # Simple analysis - count lines that might indicate monitored operations
            monitored_count = 0
            with open(trace_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    # Look for patterns that indicate monitored operations
                    if any(keyword in line.lower() for keyword in [
                        'cipher', 'encrypt', 'decrypt', 'hash', 'signature',
                        'monitored', 'violation', 'specification'
                    ]):
                        monitored_count += 1

            return monitored_count

        except Exception as e:
            self.logger.warning(f"Failed to analyze trace file for monitored operations: {str(e)}")
            return 0

    def _extract_trace_metrics(self, trace_file: str) -> Dict[str, Any]:
        """
        Extract additional metrics from the trace file.

        Args:
            trace_file: Path to the trace file

        Returns:
            Dictionary containing trace-based metrics
        """
        try:
            if not os.path.exists(trace_file):
                return {}

            # Get basic file information
            file_size = os.path.getsize(trace_file)
            
            # Count lines in trace file
            line_count = 0
            with open(trace_file, 'r', encoding='utf-8', errors='ignore') as f:
                line_count = sum(1 for _ in f)

            return {
                "trace_file_size": file_size,
                "trace_line_count": line_count,
                "trace_file_exists": True,
                "trace_level": self.tool_config['trace_level']
            }

        except Exception as e:
            self.logger.warning(f"Failed to extract trace metrics: {str(e)}")
            return {"trace_file_exists": False}

    def get_tool_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about the Humanoid tool.

        Returns:
            Dictionary containing tool metadata and configuration
        """
        return {
            "name": self.name,
            "description": self.description,
            "type": "ai_guided",
            "category": "ai_guided",
            "version": "1.0.0",
            "capabilities": self.TOOL_SPEC.capabilities,
            "supported_platforms": ["android"],
            "configuration": dict(self.tool_config),
            "execution_pattern": self.process_pattern,
            "requires_adb": True,
            "requires_droidbot": True,
            "humanoid_url": self.tool_config.get('humanoid_url'),
            "human_like_testing_support": True,
            "computer_vision_support": self.tool_config.get('vision_enabled', True),
            "natural_language_support": self.tool_config.get('nlp_enabled', True),
            "monitored_operations_support": True
        }

    def __str__(self) -> str:
        """String representation of the Humanoid tool."""
        return f"HumanoidTool(name='{self.name}', configured={bool(self.tool_config)})"

    def __repr__(self) -> str:
        """Detailed string representation of the Humanoid tool."""
        return (f"HumanoidTool(name='{self.name}', description='{self.description}', "
                f"humanoid_url='{self.tool_config.get('humanoid_url')}', "
                f"config_keys={list(self.tool_config.keys())})")
