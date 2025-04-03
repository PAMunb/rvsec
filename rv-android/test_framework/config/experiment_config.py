"""
Experiment configuration model and validation.

Defines the structure for experiment configurations, including validation
and serialization/deserialization to/from JSON.
"""
import json
import logging
import os
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import List, Dict, Any, Optional, Union, Set


class ExecutionMode(Enum):
    """Execution mode for experiment."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HYBRID = "hybrid"


@dataclass
class LLMConfig:
    """
    Configuration for a language model.
    
    Attributes:
        model_type: Type of model ('ollama', 'huggingface', etc.)
        model_name: Name of the model
        parameters: Additional parameters for the model
    """
    model_type: str
    model_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyConfig:
    """
    Configuration for a prompt strategy.
    
    Attributes:
        strategy_type: Type of prompt strategy
        parameters: Additional parameters for the strategy
    """
    strategy_type: str
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestConfiguration:
    """
    Complete configuration for a test setup.
    
    Attributes:
        name: Name/identifier of the configuration
        llm: LLM configuration
        strategy: Strategy configuration
        parameters: Additional general parameters
    """
    name: str
    llm: LLMConfig
    strategy: StrategyConfig
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionConfig:
    """
    Configuration for test execution.
    
    Attributes:
        mode: Execution mode (sequential, parallel, hybrid)
        max_parallel_instances: Maximum number of parallel instances
        unload_models: Whether to unload models between tests
        memory_threshold: Memory threshold for resource management
        resource_monitoring: Whether to monitor resources
    """
    mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    max_parallel_instances: int = 1
    unload_models: bool = True
    memory_threshold: int = 80
    resource_monitoring: bool = True


@dataclass
class ExperimentConfig:
    """
    Complete experiment configuration.
    
    ### Architectural Decisions:
    - Uses a structured data model for type safety and validation
    - Provides serialization/deserialization for persistence
    - Encapsulates all aspects of experiment configuration
    - Enables validation to ensure configuration integrity
    
    ### Role in the System:
    - Defines what experiments will be run
    - Specifies combinations of apps, configurations, and timeouts
    - Controls execution parameters like repetitions and parallelism
    - Serializes to/from JSON for sharing and storage
    
    Attributes:
        name: Name of the experiment
        description: Description of the experiment
        apps: List of application paths to test
        configurations: List of test configurations
        timeouts: List of timeouts to try for each combination
        repetitions: Number of repetitions for each combination
        metrics: List of metrics to collect
        execution: Execution configuration
    """
    name: str
    description: str
    apps: List[str]
    configurations: List[TestConfiguration]
    timeouts: List[int]
    repetitions: int = 1
    metrics: List[str] = field(default_factory=lambda: ["coverage", "mop_errors", "response_time"])
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExperimentConfig':
        """
        Create an ExperimentConfig from a dictionary.
        
        Args:
            data: Dictionary representation of an experiment config
            
        Returns:
            ExperimentConfig instance
        """
        # Process configurations
        configurations = []
        for config_data in data.get("configurations", []):
            llm_data = config_data.get("llm", {})
            if isinstance(llm_data, dict):
                llm_config = LLMConfig(
                    model_type=llm_data.get("model_type", ""),
                    model_name=llm_data.get("model_name", ""),
                    parameters=llm_data.get("parameters", {})
                )
            else:
                # Backward compatibility for flat structure
                llm_config = LLMConfig(
                    model_type=config_data.get("model_type", ""),
                    model_name=config_data.get("model_name", ""),
                    parameters={k: v for k, v in config_data.get("parameters", {}).items() 
                                if k not in ["strategy_type"]}
                )
            
            strategy_data = config_data.get("strategy", {})
            if isinstance(strategy_data, dict):
                strategy_config = StrategyConfig(
                    strategy_type=strategy_data.get("strategy_type", ""),
                    parameters=strategy_data.get("parameters", {})
                )
            else:
                # Backward compatibility for flat structure
                strategy_config = StrategyConfig(
                    strategy_type=config_data.get("strategy_type", ""),
                    parameters={}
                )
            
            configurations.append(TestConfiguration(
                name=config_data.get("name", f"config_{len(configurations)}"),
                llm=llm_config,
                strategy=strategy_config,
                parameters=config_data.get("parameters", {})
            ))
        
        # Process execution config
        execution_data = data.get("execution", {})
        mode_str = execution_data.get("mode", "sequential")
        try:
            mode = ExecutionMode(mode_str)
        except ValueError:
            mode = ExecutionMode.SEQUENTIAL
            
        execution_config = ExecutionConfig(
            mode=mode,
            max_parallel_instances=execution_data.get("max_parallel_instances", 1),
            unload_models=execution_data.get("unload_models", True),
            memory_threshold=execution_data.get("memory_threshold", 80),
            resource_monitoring=execution_data.get("resource_monitoring", True)
        )
        
        return cls(
            name=data.get("name", "untitled_experiment"),
            description=data.get("description", ""),
            apps=data.get("apps", []),
            configurations=configurations,
            timeouts=data.get("timeouts", [60]),
            repetitions=data.get("repetitions", 1),
            metrics=data.get("metrics", ["coverage", "mop_errors", "response_time"]),
            execution=execution_config
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ExperimentConfig':
        """
        Create an ExperimentConfig from a JSON string.
        
        Args:
            json_str: JSON string representation
            
        Returns:
            ExperimentConfig instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def from_file(cls, file_path: str) -> 'ExperimentConfig':
        """
        Create an ExperimentConfig from a JSON file.
        
        Args:
            file_path: Path to JSON config file
            
        Returns:
            ExperimentConfig instance
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            json.JSONDecodeError: If the file contains invalid JSON
        """
        with open(file_path, 'r') as f:
            return cls.from_json(f.read())
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Returns:
            Dictionary representation
        """
        result = asdict(self)
        # Convert enum to string
        result["execution"]["mode"] = self.execution.mode.value
        return result
    
    def to_json(self, indent: int = 2) -> str:
        """
        Convert to JSON string.
        
        Args:
            indent: Indentation level
            
        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=indent)
    
    def save(self, file_path: str) -> None:
        """
        Save configuration to a JSON file.
        
        Args:
            file_path: Path to save the file
            
        Raises:
            IOError: If the file cannot be written
        """
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(self.to_json())
    
    def validate(self) -> List[str]:
        """
        Validate the configuration.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check required fields
        if not self.name:
            errors.append("Experiment name is required")
        
        if not self.apps:
            errors.append("At least one app must be specified")
        
        if not self.configurations:
            errors.append("At least one configuration must be specified")
        
        if not self.timeouts:
            errors.append("At least one timeout must be specified")
        
        # Validate configurations
        for i, config in enumerate(self.configurations):
            if not config.name:
                errors.append(f"Configuration {i} is missing a name")
            
            if not config.llm.model_type:
                errors.append(f"Configuration '{config.name}' is missing model_type")
            
            if not config.llm.model_name:
                errors.append(f"Configuration '{config.name}' is missing model_name")
            
            if not config.strategy.strategy_type:
                errors.append(f"Configuration '{config.name}' is missing strategy_type")
        
        # Validate timeouts
        for timeout in self.timeouts:
            if timeout <= 0:
                errors.append(f"Timeout {timeout} must be positive")
        
        # Validate repetitions
        if self.repetitions <= 0:
            errors.append("Repetitions must be positive")
        
        # Validate execution
        if self.execution.mode == ExecutionMode.PARALLEL and self.execution.max_parallel_instances <= 0:
            errors.append("max_parallel_instances must be positive for parallel execution")
        
        return errors
    
    def is_valid(self) -> bool:
        """
        Check if the configuration is valid.
        
        Returns:
            True if valid, False otherwise
        """
        return len(self.validate()) == 0
    
    def get_total_combinations(self) -> int:
        """
        Get the total number of test combinations.
        
        Returns:
            Number of combinations (apps × configurations × timeouts × repetitions)
        """
        return len(self.apps) * len(self.configurations) * len(self.timeouts) * self.repetitions


class ExperimentRegistry:
    """
    Registry for experiment configurations.
    
    ### Architectural Decisions:
    - Provides a centralized registry for experiment configurations
    - Supports loading, saving, and managing configurations
    - Ensures configuration validity before registration
    
    ### Role in the System:
    - Manages experiment configurations
    - Provides access to configurations by name
    - Supports persistence of configurations
    """
    
    def __init__(self, base_dir: str = None):
        """
        Initialize the registry.
        
        Args:
            base_dir: Base directory for configuration files
        """
        self.logger = logging.getLogger(__name__)
        self.base_dir = base_dir or os.path.join(os.getcwd(), "experiments")
        self.experiments: Dict[str, ExperimentConfig] = {}
        
        # Create base directory if it doesn't exist
        os.makedirs(self.base_dir, exist_ok=True)
    
    def register(self, config: ExperimentConfig) -> bool:
        """
        Register an experiment configuration.
        
        Args:
            config: Experiment configuration to register
            
        Returns:
            True if registered successfully, False otherwise
        """
        # Validate configuration
        if not config.is_valid():
            errors = config.validate()
            self.logger.error(f"Invalid experiment configuration '{config.name}': {errors}")
            return False
        
        # Check for name collision
        if config.name in self.experiments:
            self.logger.warning(f"Overwriting existing experiment '{config.name}'")
        
        # Register configuration
        self.experiments[config.name] = config
        self.logger.info(f"Registered experiment '{config.name}'")
        
        return True
    
    def get(self, name: str) -> Optional[ExperimentConfig]:
        """
        Get an experiment configuration by name.
        
        Args:
            name: Name of the experiment
            
        Returns:
            ExperimentConfig if found, None otherwise
        """
        return self.experiments.get(name)
    
    def list_experiments(self) -> List[str]:
        """
        Get names of all registered experiments.
        
        Returns:
            List of experiment names
        """
        return list(self.experiments.keys())
    
    def load_from_file(self, file_path: str) -> Optional[ExperimentConfig]:
        """
        Load an experiment configuration from a file.
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            ExperimentConfig if loaded successfully, None otherwise
        """
        try:
            config = ExperimentConfig.from_file(file_path)
            if self.register(config):
                return config
        except Exception as e:
            self.logger.error(f"Failed to load experiment from {file_path}: {e}")
        
        return None
    
    def save_to_file(self, name: str, file_path: Optional[str] = None) -> bool:
        """
        Save an experiment configuration to a file.
        
        Args:
            name: Name of the experiment
            file_path: Path to save to (if None, uses name in base_dir)
            
        Returns:
            True if saved successfully, False otherwise
        """
        config = self.get(name)
        if not config:
            self.logger.error(f"Experiment '{name}' not found")
            return False
        
        if not file_path:
            file_path = os.path.join(self.base_dir, f"{name}.json")
        
        try:
            config.save(file_path)
            self.logger.info(f"Saved experiment '{name}' to {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save experiment '{name}': {e}")
            return False
    
    def load_all_from_directory(self, directory: Optional[str] = None) -> int:
        """
        Load all experiment configurations from a directory.
        
        Args:
            directory: Directory to load from (if None, uses base_dir)
            
        Returns:
            Number of successfully loaded configurations
        """
        directory = directory or self.base_dir
        
        if not os.path.isdir(directory):
            self.logger.warning(f"Directory '{directory}' does not exist")
            return 0
        
        count = 0
        for filename in os.listdir(directory):
            if filename.endswith('.json'):
                file_path = os.path.join(directory, filename)
                if self.load_from_file(file_path):
                    count += 1
        
        self.logger.info(f"Loaded {count} experiment configurations from {directory}")
        return count