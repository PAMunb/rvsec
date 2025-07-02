"""
QTesting tool implementation for monitored operations testing.

This module provides integration with the QTesting reinforcement learning-based
Android testing framework for intelligent exploration and testing.
"""

import os
from typing import Dict, Any, Optional, List

from rv_android_core.app import App
from rv_android_core.commands.command import Command
from rv_android_core.tools.configurable_tool import ConfigurableTool
from rv_android_core.tools.tool_spec import ToolSpec, ToolType, ToolCategory
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT


class QTestingTool(ConfigurableTool):
    """
    QTesting reinforcement learning-based testing tool for monitored operations.

    ### Architectural Decisions:
    - Extends ConfigurableTool to leverage standardized configuration management
    - Implements Python-based execution model with virtual environment support
    - Provides reinforcement learning-driven exploration strategies for intelligent testing
    - Uses configuration file-based parameter management for flexible customization
    - Supports adaptive learning algorithms for optimal test case generation
    - Integrates with rv-android-core infrastructure for error handling and logging

    ### Role in the System:
    - Serves as an intelligent testing tool using reinforcement learning algorithms
    - Provides adaptive exploration strategies that learn from application behavior
    - Enables systematic test case generation with configurable learning parameters
    - Supports both JCA cryptography detection and generic monitored operations testing
    - Facilitates research-oriented testing with machine learning capabilities
    - Generates comprehensive trace files for analysis and learning improvement

    ### Key Considerations:
    - Uses Python virtual environment for isolated execution and dependency management
    - Supports reinforcement learning algorithms with configurable parameters
    - Provides adaptive exploration that improves over multiple test runs
    - Handles dynamic configuration file generation for runtime parameter adjustment
    - Integrates with Android Debug Bridge (ADB) for device communication
    - Supports configurable test indices for experiment reproducibility

    ### Integration Strategy:
    - Compatible with experiment task execution system for automated workflows
    - Supports configuration inheritance from experiment and variant specifications
    - Enables result collection and analysis through standardized trace file format
    - Provides clear extension points for custom learning algorithms and strategies
    - Facilitates integration with coverage analysis and behavioral pattern recognition
    - Supports plugin-based architecture for external tool ecosystem integration

    ### Performance and Scalability:
    - Optimized for efficient resource utilization through virtual environment isolation
    - Supports configurable timeout mechanisms to prevent resource exhaustion
    - Enables parallel execution across multiple device instances and applications
    - Provides learning state persistence for improved performance over time
    - Scales effectively for large-scale experiment execution scenarios
    - Adaptable to different APK complexity and learning requirements
    """

    # Tool specification with comprehensive metadata
    TOOL_SPEC = ToolSpec.create_builtin_spec(
        name="qtesting",
        description="QTesting reinforcement learning-based Android testing framework",
        category=ToolCategory.AI_GUIDED,
        capabilities=[
            "reinforcement_learning",
            "adaptive_exploration",
            "intelligent_testing",
            "learning_based_strategies",
            "behavioral_analysis",
            "monitored_operations_testing"
        ]
    )

    def __init__(self):
        """
        Initialize the QTesting tool with default configuration and rv-android-core infrastructure.
        
        ### Infrastructure Integration:
        - Sets up standardized logging with QTesting-specific context
        - Initializes error handler for comprehensive error management
        - Configures QTesting-specific parameters and learning settings
        - Establishes integration with monitored operations framework
        """
        super().__init__(
            name="qtesting",
            description="QTesting reinforcement learning-based Android testing framework",
            process_pattern="python main.py"
        )

        # Initialize rv-android-core infrastructure components
        self._logging_manager = LoggingManager.get_instance()
        self.logger = self._logging_manager.get_logger(
            "rv_tools.builtin.qtesting",
            {CONTEXT_COMPONENT: "QTestingTool"}
        )
        self.error_handler = ErrorHandler.get_instance()

        # Default tool configuration
        self.default_config = {
            "test_index": 1,
            "device_id": "emulator-5554",
            "time_limit": 600,  # 10 minutes
            "learning_rate": 0.01,
            "exploration_rate": 0.1,
            "max_episodes": 1000,
            "batch_size": 32,
            "memory_size": 10000,
            "target_update_frequency": 100,
            "reward_strategy": "coverage",
            "state_representation": "screen",
            "action_space": "ui_elements",
            "enable_learning": True,
            "save_model": True,
            "load_pretrained": False,
            "model_path": None,
            "debug_mode": False
        }

        self.logger.info("QTesting tool initialized successfully")

    def configure_tool_specific(self, config: Dict[str, Any]) -> None:
        """
        Configure QTesting-specific parameters and validate settings.

        Args:
            config: Configuration dictionary with tool-specific parameters

        Raises:
            ValueError: If configuration parameters are invalid
        """
        self.logger.debug("Configuring QTesting-specific parameters")

        # Test index configuration
        if 'test_index' in config:
            test_index = config['test_index']
            if not isinstance(test_index, int) or test_index < 1:
                raise ValueError("test_index must be a positive integer")
            self.tool_config['test_index'] = test_index

        # Device configuration
        if 'device_id' in config:
            self.tool_config['device_id'] = str(config['device_id'])

        # Time limit configuration
        if 'time_limit' in config:
            time_limit = config['time_limit']
            if not isinstance(time_limit, int) or time_limit < 1:
                raise ValueError("time_limit must be a positive integer")
            self.tool_config['time_limit'] = time_limit

        # Learning parameters
        if 'learning_rate' in config:
            learning_rate = config['learning_rate']
            if not isinstance(learning_rate, (int, float)) or learning_rate <= 0:
                raise ValueError("learning_rate must be a positive number")
            self.tool_config['learning_rate'] = learning_rate

        if 'exploration_rate' in config:
            exploration_rate = config['exploration_rate']
            if not isinstance(exploration_rate, (int, float)) or not (0 <= exploration_rate <= 1):
                raise ValueError("exploration_rate must be between 0 and 1")
            self.tool_config['exploration_rate'] = exploration_rate

        # Episode and batch configuration
        for param in ['max_episodes', 'batch_size', 'memory_size', 'target_update_frequency']:
            if param in config:
                value = config[param]
                if not isinstance(value, int) or value < 1:
                    raise ValueError(f"{param} must be a positive integer")
                self.tool_config[param] = value

        # Strategy configuration
        if 'reward_strategy' in config:
            strategy = config['reward_strategy']
            valid_strategies = ['coverage', 'novelty', 'hybrid', 'user_defined']
            if strategy not in valid_strategies:
                raise ValueError(f"reward_strategy must be one of: {valid_strategies}")
            self.tool_config['reward_strategy'] = strategy

        if 'state_representation' in config:
            representation = config['state_representation']
            valid_representations = ['screen', 'ui_hierarchy', 'features', 'combined']
            if representation not in valid_representations:
                raise ValueError(f"state_representation must be one of: {valid_representations}")
            self.tool_config['state_representation'] = representation

        if 'action_space' in config:
            action_space = config['action_space']
            valid_spaces = ['ui_elements', 'coordinates', 'gestures', 'hybrid']
            if action_space not in valid_spaces:
                raise ValueError(f"action_space must be one of: {valid_spaces}")
            self.tool_config['action_space'] = action_space

        # Model path configuration
        if 'model_path' in config:
            model_path = config['model_path']
            if model_path and not os.path.exists(model_path):
                raise ValueError(f"model_path does not exist: {model_path}")
            self.tool_config['model_path'] = model_path

        # Boolean flags
        boolean_flags = [
            'enable_learning', 'save_model', 'load_pretrained', 'debug_mode'
        ]
        
        for flag in boolean_flags:
            if flag in config:
                self.tool_config[flag] = bool(config[flag])

        self.logger.info("QTesting tool configuration completed successfully")

    def _create_config_file(self, app: App, task_config: Dict[str, Any]) -> str:
        """
        Create QTesting configuration file with current settings.

        Args:
            app: Application instance
            task_config: Task-specific configuration

        Returns:
            Path to created configuration file
        """
        try:
            # Get QTesting directory
            tools_dir = os.environ.get('TOOLS_DIR', '/tools')
            qtesting_dir = os.path.join(tools_dir, 'qtesting', 'src')
            config_file = os.path.join(qtesting_dir, 'conf.txt')

            # Ensure directory exists
            os.makedirs(qtesting_dir, exist_ok=True)

            # Get timeout from task or tool config
            timeout_seconds = task_config.get('timeout', self.tool_config['time_limit'])

            # Create configuration content
            config_content = f"""[Path]
Benchmark = 
APK_NAME = {app.path}

[Setting]
DEVICE_ID = {self.tool_config['device_id']}
TIME_LIMIT = {timeout_seconds}
TEST_INDEX = {self.tool_config['test_index']}

[Learning]
LEARNING_RATE = {self.tool_config['learning_rate']}
EXPLORATION_RATE = {self.tool_config['exploration_rate']}
MAX_EPISODES = {self.tool_config['max_episodes']}
BATCH_SIZE = {self.tool_config['batch_size']}
MEMORY_SIZE = {self.tool_config['memory_size']}
TARGET_UPDATE_FREQUENCY = {self.tool_config['target_update_frequency']}

[Strategy]
REWARD_STRATEGY = {self.tool_config['reward_strategy']}
STATE_REPRESENTATION = {self.tool_config['state_representation']}
ACTION_SPACE = {self.tool_config['action_space']}

[Model]
ENABLE_LEARNING = {self.tool_config['enable_learning']}
SAVE_MODEL = {self.tool_config['save_model']}
LOAD_PRETRAINED = {self.tool_config['load_pretrained']}
MODEL_PATH = {self.tool_config.get('model_path', '')}

[Debug]
DEBUG_MODE = {self.tool_config['debug_mode']}
"""

            # Write configuration file
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(config_content)

            self.logger.debug(f"QTesting configuration file created: {config_file}")
            return config_file

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "create_config_file",
                    "app_name": app.name,
                    "tool": "qtesting",
                    "component": "QTestingTool"
                }
            )
            raise

    def build_command_args(self, app: App, output_file: str, task_config: Dict[str, Any]) -> List[str]:
        """
        Build command arguments for QTesting execution.

        Args:
            app: Application instance containing APK information
            output_file: Path to output trace file
            task_config: Task-specific configuration parameters

        Returns:
            List of command arguments for tool execution
        """
        try:
            self.logger.debug(f"Building QTesting command arguments for app: {app.name}")

            # Get QTesting script path
            tools_dir = os.environ.get('TOOLS_DIR', '/tools')
            qtesting_script = os.path.join(tools_dir, 'qtesting', 'src', 'main.py')

            # Create configuration file
            config_file = self._create_config_file(app, task_config)

            # Build comprehensive argument list
            args = [
                qtesting_script,
                "-r", config_file
            ]

            # Add debug flag if enabled
            if self.tool_config['debug_mode']:
                args.append("--debug")

            self.logger.debug(f"QTesting command arguments: {args}")
            return args

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "build_command_args",
                    "app_name": app.name,
                    "tool": "qtesting",
                    "component": "QTestingTool"
                }
            )
            raise

    def validate_execution_environment(self, app: App) -> bool:
        """
        Validate that the execution environment is properly configured for QTesting.

        Args:
            app: Application instance to validate against

        Returns:
            True if environment is valid, False otherwise
        """
        try:
            self.logger.debug("Validating QTesting execution environment")

            # Check if Python is available
            try:
                python_check = Command("python", ["--version"], timeout=10)
                result = python_check.invoke()
                if result.returncode != 0:
                    self.logger.error("Python is not available or not responding")
                    return False
            except Exception as e:
                self.logger.error(f"Python validation failed: {str(e)}")
                return False

            # Validate QTesting directory structure
            tools_dir = os.environ.get('TOOLS_DIR', '/tools')
            qtesting_dir = os.path.join(tools_dir, 'qtesting', 'src')
            qtesting_script = os.path.join(qtesting_dir, 'main.py')

            if not os.path.exists(qtesting_dir):
                self.logger.error(f"QTesting directory not found: {qtesting_dir}")
                return False

            if not os.path.exists(qtesting_script):
                self.logger.error(f"QTesting script not found: {qtesting_script}")
                return False

            # Validate APK file
            if not os.path.exists(app.path):
                self.logger.error(f"APK file not found: {app.path}")
                return False

            # Check virtual environment if exists
            venv_python = os.path.join(tools_dir, 'qtesting', 'venv', 'bin', 'python')
            if os.path.exists(venv_python):
                self.logger.info("QTesting virtual environment detected")

            self.logger.info("QTesting execution environment validation successful")
            return True

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "validate_execution_environment",
                    "app_name": app.name,
                    "tool": "qtesting",
                    "component": "QTestingTool"
                }
            )
            return False

    def get_execution_command(self, app: App, output_file: str, task_config: Dict[str, Any]) -> Command:
        """
        Create the execution command for QTesting tool.

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
            timeout_seconds = task_config.get('timeout', self.tool_config['time_limit'])
            execution_timeout = timeout_seconds + 30  # Add 30 second buffer

            # Check for virtual environment
            tools_dir = os.environ.get('TOOLS_DIR', '/tools')
            venv_python = os.path.join(tools_dir, 'qtesting', 'venv', 'bin', 'python')
            python_executable = venv_python if os.path.exists(venv_python) else "python"

            # Create command with comprehensive configuration
            command = Command(
                executable=python_executable,
                args=args,
                timeout=execution_timeout,
                working_directory=os.path.join(tools_dir, 'qtesting', 'src')
            )

            self.logger.info(f"QTesting execution command created for app: {app.name}")
            return command

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "get_execution_command",
                    "app_name": app.name,
                    "tool": "qtesting",
                    "component": "QTestingTool"
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
            self.logger.debug(f"Processing QTesting execution result for app: {app.name}")

            # Base result information
            execution_result = {
                "tool": "qtesting",
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
                    "learning_enabled": self.tool_config['enable_learning'],
                    "test_index": self.tool_config['test_index'],
                    "monitored_operations_detected": self._analyze_trace_for_monitored_operations(output_file)
                })
            else:
                execution_result.update({
                    "exploration_completed": False,
                    "timeout_occurred": result.returncode == 124,
                    "error_details": getattr(result, 'stderr', ''),
                    "monitored_operations_detected": 0
                })

            # Extract additional metrics from trace file
            if output_file and os.path.exists(output_file):
                execution_result.update(self._extract_trace_metrics(output_file))

            self.logger.info(f"QTesting execution result processed for app: {app.name}")
            return execution_result

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "process_execution_result",
                    "app_name": app.name,
                    "tool": "qtesting",
                    "component": "QTestingTool"
                }
            )
            
            return {
                "tool": "qtesting",
                "app_name": app.name,
                "success": False,
                "error": f"Result processing failed: {str(e)}"
            }

    def _analyze_trace_for_monitored_operations(self, trace_file: str) -> int:
        """Analyze trace file for monitored operations occurrences."""
        try:
            if not os.path.exists(trace_file):
                return 0
            monitored_count = 0
            with open(trace_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if any(keyword in line.lower() for keyword in [
                        'cipher', 'encrypt', 'decrypt', 'hash', 'signature',
                        'monitored', 'violation', 'specification'
                    ]):
                        monitored_count += 1
            return monitored_count
        except Exception as e:
            self.logger.warning(f"Failed to analyze trace file: {str(e)}")
            return 0

    def _extract_trace_metrics(self, trace_file: str) -> Dict[str, Any]:
        """Extract additional metrics from the trace file."""
        try:
            if not os.path.exists(trace_file):
                return {}
            file_size = os.path.getsize(trace_file)
            line_count = 0
            with open(trace_file, 'r', encoding='utf-8', errors='ignore') as f:
                line_count = sum(1 for _ in f)
            return {
                "trace_file_size": file_size,
                "trace_line_count": line_count,
                "trace_file_exists": True
            }
        except Exception as e:
            self.logger.warning(f"Failed to extract trace metrics: {str(e)}")
            return {"trace_file_exists": False}

    def get_tool_info(self) -> Dict[str, Any]:
        """Get comprehensive information about the QTesting tool."""
        return {
            "name": self.name,
            "description": self.description,
            "type": "machine_learning",
            "category": "testing",
            "version": "1.0.0",
            "capabilities": self.TOOL_SPEC.capabilities,
            "supported_platforms": self.TOOL_SPEC.supported_platforms,
            "resource_requirements": self.TOOL_SPEC.resource_requirements,
            "configuration": dict(self.tool_config),
            "execution_pattern": self.process_pattern,
            "requires_python": True,
            "monitored_operations_support": True
        }

    def __str__(self) -> str:
        """String representation of the QTesting tool."""
        return f"QTestingTool(name='{self.name}', configured={bool(self.tool_config)})"

    def __repr__(self) -> str:
        """Detailed string representation of the QTesting tool."""
        return (f"QTestingTool(name='{self.name}', description='{self.description}', "
                f"config_keys={list(self.tool_config.keys())})")