"""
QTesting reinforcement learning based testing tool implementation.

This module provides integration with the QTesting Android testing framework,
enabling intelligent testing through reinforcement learning algorithms.
"""

import os
from typing import Dict, Any, List

from rv_android_core.domain.app import App
from rv_android_core.commands.command import Command
from rv_android_core.domain.task import Task
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT


class QTestingTool(AbstractTool):
    """
    QTesting reinforcement learning based intelligent testing framework.

    ### Architectural Decisions:
    - Inherits directly from AbstractTool for simplified architecture
    - Implements reinforcement learning algorithms for intelligent test generation
    - Provides adaptive testing strategies based on application feedback
    - Uses Docker-based execution model for environment isolation
    - Supports multiple learning algorithms and configuration options
    - Integrates with rv-android-core infrastructure for error handling and logging

    ### Role in the System:
    - Serves as an intelligent testing tool using reinforcement learning algorithms
    - Provides adaptive test generation based on application behavior feedback
    - Enables intelligent exploration using Q-learning and related algorithms
    - Supports both JCA cryptography detection and generic monitored operations testing
    - Facilitates advanced testing through machine learning-guided exploration

    ### Key Features:
    - Reinforcement learning based test generation
    - Q-learning and deep Q-network (DQN) algorithms
    - Adaptive exploration strategies with reward-based learning
    - Docker-based execution for environment consistency
    - Integration with Android Debug Bridge (ADB) for device communication

    ### Tool Variants:
    QTesting supports different learning algorithms as variants:
    - qlearning: Standard Q-learning algorithm
    - dqn: Deep Q-Network algorithm
    - ddqn: Double Deep Q-Network algorithm
    """

    # Simplified tool specification
    TOOL_SPEC = ToolSpec.create_builtin_spec(
        name="qtesting",
        description="QTesting reinforcement learning based intelligent testing framework",
        url="https://github.com/ZIMBABWEchiedza/qtesting",
        version="1.0.0",
        process_pattern="qtesting"
    )

    # Available learning algorithms
    AVAILABLE_ALGORITHMS = [
        'qlearning', 'dqn', 'ddqn', 'sarsa', 'actor_critic'
    ]

    def __init__(self, name: str = None, description: str = None, process_pattern: str = None):
        """
        Initialize the QTesting tool with rv-android-core infrastructure.
        """
        super().__init__(
            name=name or self.TOOL_SPEC.name,
            description=description or self.TOOL_SPEC.description,
            process_pattern=process_pattern or self.TOOL_SPEC.process_pattern
        )

        # Initialize rv-android-core infrastructure components
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_tools.builtin.qtesting",
            {CONTEXT_COMPONENT: "QTestingTool"}
        )

        # Default QTesting configuration
        self.config = {
            "algorithm": "qlearning",        # Learning algorithm
            "max_episodes": 1000,            # Maximum episodes for training
            "device_serial": None,           # Device serial number
            "docker_image": "qtesting:latest", # Docker image to use
            "container_name": None,          # Container name (auto-generated)
            "timeout": 3600,                 # Execution timeout in seconds (1 hour)
            "debug_mode": False,             # Enable debug mode
            "learning_rate": 0.1,            # Learning rate for RL algorithms
            "discount_factor": 0.95,         # Discount factor (gamma)
            "epsilon": 0.1,                  # Exploration rate (epsilon)
            "epsilon_decay": 0.995,          # Epsilon decay rate
            "batch_size": 32,                # Batch size for DQN
            "memory_size": 10000,            # Replay memory size
            "update_frequency": 100,         # Model update frequency
            "cleanup_container": True,       # Clean up container after execution
            "save_model": True,              # Save trained model
            "load_pretrained": False         # Load pretrained model
        }

        self.logger.info("Initialized QTesting tool for RL-based exploration")

    @classmethod
    def get_tool_spec(cls):
        """Get tool specification for registration."""
        return cls.TOOL_SPEC
    
    @classmethod
    def get_variants(cls) -> Dict[str, Dict[str, Any]]:
        """Get available QTesting variants with different RL algorithms."""
        return {
            "default": {
                "algorithm": "qlearning",
                "max_episodes": 1000,
                "timeout": 3600,
                "debug_mode": False,
                "learning_rate": 0.1,
                "discount_factor": 0.95,
                "epsilon": 0.1,
                "epsilon_decay": 0.995,
                "cleanup_container": True,
                "save_model": True,
                "load_pretrained": False
            },
            "qlearning": {
                "algorithm": "qlearning",
                "max_episodes": 1500,
                "timeout": 2700,
                "debug_mode": False,
                "learning_rate": 0.15,
                "discount_factor": 0.9,
                "epsilon": 0.2,
                "epsilon_decay": 0.99,
                "cleanup_container": True,
                "save_model": True,
                "load_pretrained": False
            },
            "dqn": {
                "algorithm": "dqn",
                "max_episodes": 2000,
                "timeout": 5400,
                "debug_mode": True,
                "learning_rate": 0.001,
                "discount_factor": 0.99,
                "epsilon": 0.1,
                "epsilon_decay": 0.995,
                "batch_size": 64,
                "memory_size": 20000,
                "update_frequency": 50,
                "cleanup_container": True,
                "save_model": True,
                "load_pretrained": False
            },
            "ddqn": {
                "algorithm": "ddqn",
                "max_episodes": 2500,
                "timeout": 7200,
                "debug_mode": True,
                "learning_rate": 0.0005,
                "discount_factor": 0.99,
                "epsilon": 0.05,
                "epsilon_decay": 0.999,
                "batch_size": 128,
                "memory_size": 50000,
                "update_frequency": 25,
                "cleanup_container": False,
                "save_model": True,
                "load_pretrained": True
            }
        }

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure QTesting-specific parameters.

        Supported configuration options:
        - algorithm: Learning algorithm (qlearning, dqn, ddqn, sarsa, actor_critic)
        - max_episodes: Maximum episodes for training
        - device_serial: Device serial number
        - docker_image: Docker image to use
        - container_name: Container name
        - timeout: Execution timeout in seconds
        - debug_mode: Enable debug mode
        - learning_rate: Learning rate for RL algorithms
        - discount_factor: Discount factor (gamma)
        - epsilon: Exploration rate (epsilon)
        - epsilon_decay: Epsilon decay rate
        - batch_size: Batch size for DQN
        - memory_size: Replay memory size
        - update_frequency: Model update frequency
        - cleanup_container: Clean up container after execution
        - save_model: Save trained model
        - load_pretrained: Load pretrained model

        Args:
            config: Configuration dictionary with QTesting parameters
        """
        if not config:
            return

        # Update algorithm
        if 'algorithm' in config:
            algorithm = config['algorithm']
            if algorithm not in self.AVAILABLE_ALGORITHMS:
                self.logger.warning(f"Invalid algorithm '{algorithm}'. Using default 'qlearning'")
                self.logger.warning(f"Available algorithms: {self.AVAILABLE_ALGORITHMS}")
            else:
                self.config['algorithm'] = algorithm
                self.logger.debug(f"Set QTesting algorithm to: {algorithm}")

        # Update max episodes
        if 'max_episodes' in config:
            try:
                episodes = int(config['max_episodes'])
                if episodes > 0:
                    self.config['max_episodes'] = episodes
                    self.logger.debug(f"Set QTesting max episodes to: {episodes}")
                else:
                    self.logger.warning("Max episodes must be positive")
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid max_episodes value: {config['max_episodes']}")

        # Update device serial
        if 'device_serial' in config:
            self.config['device_serial'] = config['device_serial']
            self.logger.debug(f"Set QTesting device serial to: {config['device_serial']}")

        # Update Docker image
        if 'docker_image' in config:
            self.config['docker_image'] = str(config['docker_image'])
            self.logger.debug(f"Set QTesting Docker image to: {config['docker_image']}")

        # Update container name
        if 'container_name' in config:
            self.config['container_name'] = str(config['container_name'])
            self.logger.debug(f"Set QTesting container name to: {config['container_name']}")

        # Update timeout
        if 'timeout' in config:
            try:
                timeout = int(config['timeout'])
                if timeout > 0:
                    self.config['timeout'] = timeout
                    self.logger.debug(f"Set QTesting timeout to: {timeout}s")
                else:
                    self.logger.warning("Timeout must be positive")
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid timeout value: {config['timeout']}")

        # Update learning parameters
        learning_params = {
            'learning_rate': (0.0, 1.0),
            'discount_factor': (0.0, 1.0),
            'epsilon': (0.0, 1.0),
            'epsilon_decay': (0.0, 1.0)
        }
        
        for param, (min_val, max_val) in learning_params.items():
            if param in config:
                try:
                    value = float(config[param])
                    if min_val <= value <= max_val:
                        self.config[param] = value
                        self.logger.debug(f"Set QTesting {param} to: {value}")
                    else:
                        self.logger.warning(f"{param} must be between {min_val} and {max_val}")
                except (ValueError, TypeError):
                    self.logger.warning(f"Invalid {param} value: {config[param]}")

        # Update integer parameters
        int_params = ['batch_size', 'memory_size', 'update_frequency']
        for param in int_params:
            if param in config:
                try:
                    value = int(config[param])
                    if value > 0:
                        self.config[param] = value
                        self.logger.debug(f"Set QTesting {param} to: {value}")
                    else:
                        self.logger.warning(f"{param} must be positive")
                except (ValueError, TypeError):
                    self.logger.warning(f"Invalid {param} value: {config[param]}")

        # Update boolean flags
        boolean_flags = ['debug_mode', 'cleanup_container', 'save_model', 'load_pretrained']
        for flag in boolean_flags:
            if flag in config:
                self.config[flag] = bool(config[flag])
                self.logger.debug(f"Set QTesting {flag} to: {self.config[flag]}")

    @ErrorHandler.handle_errors(
        component="QTestingTool",
        phase="execute_tool_specific_logic"
    )
    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
        """
        Execute QTesting with configured parameters.

        ### Execution Workflow:
        1. Prepare Docker environment and RL configuration
        2. Mount necessary volumes for APK and model data
        3. Execute QTesting in Docker container with specified algorithm
        4. Capture execution output and learning metrics
        5. Save trained models and clean up resources

        Args:
            task: Task configuration containing timeout and other parameters
            app: Application under test with package name and metadata
        """
        self.logger.info(f"Executing QTesting tool for {app.package_name}")
        self.logger.debug(f"Algorithm: {self.config['algorithm']}, Max episodes: {self.config['max_episodes']}")

        # Get timeout from task configuration
        timeout_in_seconds = getattr(task.config, 'timeout', self.config['timeout'])
        
        self.logger.info(f"QTesting execution timeout: {timeout_in_seconds} seconds")

        # Create output directory for QTesting results
        output_dir = os.path.join(os.path.dirname(task.result.trace_file), "qtesting_output")
        os.makedirs(output_dir, exist_ok=True)

        # Generate container name if not provided
        if not self.config['container_name']:
            container_name = f"qtesting_{app.package_name.replace('.', '_')}"
        else:
            container_name = self.config['container_name']

        # Build QTesting Docker command
        qtesting_cmd = self._build_qtesting_command(app, output_dir, container_name, timeout_in_seconds)
        
        # Build command string for logging
        cmd_str = f"{qtesting_cmd.command} {' '.join(qtesting_cmd.args)}"
        self.logger.debug(f"QTesting command: {cmd_str}")

        # Execute QTesting testing with centralized error handling
        try:
            self.logger.info(f"Starting QTesting execution for {app.package_name}")
            
            # Execute command with output redirection (binary mode for command output)
            with open(task.result.trace_file, 'wb') as trace_file:
                # Use centralized command execution with error handling
                # Redirect both stdout and stderr to trace file to prevent console flooding
                result = self._execute_and_check_command(qtesting_cmd, stdout=trace_file, stderr=trace_file)
            
            # Append success information to trace file (text mode for metadata)
            # with open(task.result.trace_file, 'a', encoding='utf-8') as trace_file:
            #     success_info = f"\n--- QTesting Execution Completed ---\n"
            #     success_info += f"Algorithm: {self.config['algorithm']}\n"
            #     success_info += f"Max episodes: {self.config['max_episodes']}\n"
            #     success_info += f"Learning rate: {self.config['learning_rate']}\n"
            #     success_info += f"Container name: {container_name}\n"
            #     success_info += f"Output directory: {output_dir}\n"
            #     success_info += f"Command: {cmd_str}\n"
            #     trace_file.write(success_info)
            
            self.logger.info("QTesting execution completed successfully")
            
        except Exception as e:
            self.logger.error(f"QTesting execution failed: {str(e)}")
            raise
        finally:
            # Clean up container if enabled
            if self.config['cleanup_container']:
                self._cleanup_container(container_name)

    def _build_qtesting_command(self, app: App, output_dir: str, container_name: str, timeout_seconds: int) -> Command:
        """
        Build the QTesting Docker command with configured parameters.

        Args:
            app: Application under test
            output_dir: Output directory for QTesting results
            container_name: Docker container name
            timeout_seconds: Command execution timeout

        Returns:
            Configured Command object for QTesting execution
        """
        # Start building Docker command arguments
        cmd_args = [
            "run",
            "--name", container_name,
            "--rm" if self.config['cleanup_container'] else "",
            "-v", f"{app.apk_path}:/app/target.apk:ro",
            "-v", f"{output_dir}:/app/output"
        ]

        # Remove empty strings from args
        cmd_args = [arg for arg in cmd_args if arg]

        # Add environment variables for RL configuration
        env_vars = {
            "ALGORITHM": self.config["algorithm"],
            "MAX_EPISODES": str(self.config["max_episodes"]),
            "LEARNING_RATE": str(self.config["learning_rate"]),
            "DISCOUNT_FACTOR": str(self.config["discount_factor"]),
            "EPSILON": str(self.config["epsilon"]),
            "EPSILON_DECAY": str(self.config["epsilon_decay"]),
            "BATCH_SIZE": str(self.config["batch_size"]),
            "MEMORY_SIZE": str(self.config["memory_size"]),
            "UPDATE_FREQUENCY": str(self.config["update_frequency"])
        }

        for key, value in env_vars.items():
            cmd_args.extend(["-e", f"{key}={value}"])

        # Add device serial if specified
        if self.config["device_serial"]:
            cmd_args.extend(["-e", f"DEVICE_SERIAL={self.config['device_serial']}"])

        # Add Docker image
        cmd_args.append(self.config['docker_image'])

        # Add QTesting-specific arguments
        cmd_args.extend([
            "--apk", "/app/target.apk",
            "--output", "/app/output",
            "--algorithm", self.config["algorithm"],
            "--max-episodes", str(self.config["max_episodes"]),
            "--timeout", str(self.config["timeout"])
        ])

        # Add debug mode if enabled
        if self.config["debug_mode"]:
            cmd_args.append("--debug")

        # Add model saving flag
        if self.config["save_model"]:
            cmd_args.append("--save-model")

        # Add pretrained model loading flag
        if self.config["load_pretrained"]:
            cmd_args.append("--load-pretrained")

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

    def get_available_algorithms(self) -> List[str]:
        """
        Get list of available learning algorithms.

        Returns:
            List of available algorithm names
        """
        return self.AVAILABLE_ALGORITHMS.copy()

    def get_tool_info(self) -> dict:
        """
        Get comprehensive QTesting tool information.

        Returns:
            Dictionary with tool information and current configuration
        """
        info = super().get_tool_info()
        info.update({
            "tool_spec": self.TOOL_SPEC.to_dict(),
            "available_algorithms": self.get_available_algorithms(),
            "current_algorithm": self.config["algorithm"],
            "current_max_episodes": self.config["max_episodes"],
            "learning_rate": self.config["learning_rate"],
            "discount_factor": self.config["discount_factor"],
            "epsilon": self.config["epsilon"],
            "debug_mode": self.config["debug_mode"],
            "version": self.TOOL_SPEC.version,
            "url": self.TOOL_SPEC.url
        })
        return info


# Function to register QTesting variants
def register_qtesting_variants(registry):
    """
    Register QTesting variants in the tool registry.
    
    Args:
        registry: ToolRegistry instance
    """
    # Register learning algorithm variants
    variants = {
        "qlearning": {"algorithm": "qlearning", "learning_rate": 0.1},
        "dqn": {"algorithm": "dqn", "batch_size": 64, "memory_size": 50000},
        "ddqn": {"algorithm": "ddqn", "batch_size": 64, "memory_size": 50000, "update_frequency": 1000},
        "sarsa": {"algorithm": "sarsa", "learning_rate": 0.05},
        "actor_critic": {"algorithm": "actor_critic", "learning_rate": 0.01}
    }
    
    for variant_name, config in variants.items():
        registry.register_variant("qtesting", variant_name, config)