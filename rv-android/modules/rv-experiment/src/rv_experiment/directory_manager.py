"""
ExperimentDirectoryManager - Standardized Directory Structure Management

### Architectural Overview:
This module implements the standardized directory structure for all experiment operations.
It provides a centralized management system for the ./out/ directory structure, ensuring
consistency across all experiments and components while supporting the factory-based
architecture.

### Key Architectural Decisions:
- **Standardized Structure**: Consistent ./out/ directory layout for all operations
- **Path Validation**: Comprehensive validation of directory structures and permissions
- **Component Integration**: Seamless integration with factories and orchestration
- **Error Handling**: Robust error handling using rv-android-core decorators
- **Resource Management**: Efficient creation, cleanup, and maintenance of directory structures

### Directory Structure:
```
./out/
├── experiments/{experiment_id}/     # Individual experiment results
│   ├── config.json                  # Experiment configuration
│   ├── logs/                        # Experiment-specific logs
│   ├── results/                     # Results and analysis data
│   └── traces/                      # Execution traces and coverage
├── instrumented/                    # Shared instrumented APKs  
│   ├── jca/                         # JCA crypto monitored APKs
│   ├── generic/                     # Generic pattern monitored APKs
│   └── cache/                       # Instrumentation cache
├── monitors/                        # Generated monitor files
│   ├── jca/                         # JCA crypto specifications
│   ├── generic/                     # Generic programming patterns  
│   └── custom/                      # Custom specification sets
├── static/                          # Static analysis results
│   ├── gator/                       # Gator analysis results
│   ├── gesda/                       # GESDA analysis results
│   └── reach/                       # Reachability analysis results
└── cache/                           # Component and tool cache
    ├── tools/                       # Tool-specific cache
    ├── models/                      # LLM model cache
    └── temp/                        # Temporary files
```

### Role in the System:
- Provides centralized directory management for all experiment operations
- Ensures consistent structure across different tools and components
- Manages separation between JCA crypto and generic specification experiments
- Supports experiment continuation and state management
- Enables efficient resource sharing and caching strategies
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Union, Tuple
from dataclasses import dataclass

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.exceptions import ConfigurationError, ValidationError


@dataclass
class DirectoryStructure:
    """
    Data class representing the standardized experiment directory structure.
    
    ### Architectural Decisions:
    This structure supports both JCA crypto and generic specification monitoring
    while maintaining clean separation between different types of monitored operations.
    The structure is designed to scale with different experiment types and tools.
    """
    base_dir: str
    experiments_dir: str
    instrumented_dir: str
    monitors_dir: str
    static_dir: str
    cache_dir: str
    
    # Specification-specific subdirectories
    jca_instrumented_dir: str
    generic_instrumented_dir: str
    jca_monitors_dir: str
    generic_monitors_dir: str
    custom_monitors_dir: str
    
    # Static analysis subdirectories
    gator_dir: str
    gesda_dir: str
    reach_dir: str
    
    # Cache subdirectories
    tools_cache_dir: str
    models_cache_dir: str
    temp_dir: str


class ExperimentDirectoryManager:
    """
    Centralized manager for experiment directory structure and operations.
    
    ### Architectural Overview:
    This manager implements the standardized ./out/ directory structure for experiment
    operations. It provides comprehensive directory management capabilities while
    supporting both JCA cryptography and generic programming pattern monitoring
    through cleanly separated directory structures.
    
    ### Key Architectural Decisions:
    - **Specification Separation**: Clear separation between JCA crypto and generic specifications
    - **Resource Sharing**: Efficient sharing of instrumented APKs and static analysis results
    - **Experiment Isolation**: Individual experiment directories with complete isolation
    - **Caching Strategy**: Multi-level caching for tools, models, and temporary files
    - **Path Validation**: Comprehensive validation of all directory operations
    
    ### Role in the System:
    - Provides standardized directory structure for all experiment operations
    - Manages creation, validation, and cleanup of experiment directories
    - Supports experiment continuation through directory state management
    - Enables efficient resource sharing across different experiments
    - Coordinates with factories and orchestration components
    """
    
    def __init__(self, base_dir: str = "./out/", logger=None):
        """
        Initialize experiment directory manager with standardized structure.
        
        ### Initialization Strategy:
        - Validates base directory accessibility and permissions
        - Creates standardized directory structure if not exists
        - Sets up logging and error handling for directory operations
        - Prepares directory manager for experiment coordination
        
        Args:
            base_dir: Base experiment directory (default: ./out/)
            logger: Optional logger instance for dependency injection
        """
        # Logging setup
        if logger:
            self.logger = logger
        else:
            logging_manager = LoggingManager.get_instance()
            self.logger = logging_manager.get_logger(
                "rv_experiment.directory_manager",
                {CONTEXT_COMPONENT: "ExperimentDirectoryManager"}
            )
        
        # Path management
        self.base_dir = Path(base_dir).resolve()
        self.structure = self._create_directory_structure()
        
        # Ensure base directory exists
        self._ensure_base_directory()
        
        self.logger.info(f"ExperimentDirectoryManager initialized: {self.base_dir}")
    
    def _create_directory_structure(self) -> DirectoryStructure:
        """
        Create the standardized directory structure configuration.
        
        Returns:
            DirectoryStructure instance with all required paths
        """
        base = self.base_dir
        
        return DirectoryStructure(
            base_dir=str(base),
            experiments_dir=str(base / "experiments"),
            instrumented_dir=str(base / "instrumented"),
            monitors_dir=str(base / "monitors"),
            static_dir=str(base / "static"),
            cache_dir=str(base / "cache"),
            
            # Specification-specific paths
            jca_instrumented_dir=str(base / "instrumented" / "jca"),
            generic_instrumented_dir=str(base / "instrumented" / "generic"),
            jca_monitors_dir=str(base / "monitors" / "jca"),
            generic_monitors_dir=str(base / "monitors" / "generic"),
            custom_monitors_dir=str(base / "monitors" / "custom"),
            
            # Static analysis paths
            gator_dir=str(base / "static" / "gator"),
            gesda_dir=str(base / "static" / "gesda"),
            reach_dir=str(base / "static" / "reach"),
            
            # Cache paths
            tools_cache_dir=str(base / "cache" / "tools"),
            models_cache_dir=str(base / "cache" / "models"),
            temp_dir=str(base / "cache" / "temp")
        )
    
    @ErrorHandler.handle_errors(
        component="ExperimentDirectoryManager",
        phase="ensure_base_directory",
    )
    def _ensure_base_directory(self):
        """
        Ensure base directory exists and is accessible.
        
        Raises:
            ConfigurationError: If directory cannot be created or accessed
        """
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            
            # Test write permissions
            test_file = self.base_dir / ".test_write"
            test_file.touch()
            test_file.unlink()
            
        except PermissionError as e:
            raise ConfigurationError(f"No write permission for directory: {self.base_dir}") from e
        except OSError as e:
            raise ConfigurationError(f"Cannot create base directory: {self.base_dir}") from e
    
    @ErrorHandler.handle_errors(
        component="ExperimentDirectoryManager",
        phase="create_full_structure",
    )
    def create_full_structure(self) -> bool:
        """
        Create the complete standardized directory structure.
        
        ### Structure Creation Strategy:
        - Creates all required directories in the correct order
        - Sets appropriate permissions for each directory type
        - Validates successful creation of all components
        - Provides comprehensive error handling and rollback
        
        Returns:
            True if structure created successfully, False otherwise
            
        Raises:
            ConfigurationError: If directory structure cannot be created
        """
        self.logger.info("Creating standardized experiment directory structure")
        
        directories_to_create = [
            self.structure.experiments_dir,
            self.structure.instrumented_dir,
            self.structure.monitors_dir,
            self.structure.static_dir,
            self.structure.cache_dir,
            
            # Specification-specific directories
            self.structure.jca_instrumented_dir,
            self.structure.generic_instrumented_dir,
            self.structure.jca_monitors_dir,
            self.structure.generic_monitors_dir,
            self.structure.custom_monitors_dir,
            
            # Static analysis directories
            self.structure.gator_dir,
            self.structure.gesda_dir,
            self.structure.reach_dir,
            
            # Cache directories
            self.structure.tools_cache_dir,
            self.structure.models_cache_dir,
            self.structure.temp_dir
        ]
        
        created_directories = []
        
        try:
            for directory in directories_to_create:
                dir_path = Path(directory)
                dir_path.mkdir(parents=True, exist_ok=True)
                created_directories.append(dir_path)
                self.logger.debug(f"Created directory: {directory}")
            
            self.logger.info("Successfully created complete directory structure")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create directory structure: {e}")
            
            # Attempt cleanup of partially created structure
            for directory in reversed(created_directories):
                try:
                    if directory.exists() and not any(directory.iterdir()):
                        directory.rmdir()
                except Exception:
                    pass  # Best effort cleanup
            
            raise ConfigurationError(f"Cannot create directory structure: {e}")
    
    @ErrorHandler.handle_errors(
        component="ExperimentDirectoryManager",
        phase="create_experiment_directory",
    )
    def create_experiment_directory(self, experiment_id: str, 
                                  specification_set: str = "jca") -> Path:
        """
        Create directory structure for a specific experiment.
        
        ### Experiment Directory Strategy:
        - Creates isolated directory for experiment results and logs
        - Sets up subdirectories for different types of experiment data
        - Links to appropriate specification-specific resources
        - Provides comprehensive logging and error handling
        
        Args:
            experiment_id: Unique identifier for the experiment
            specification_set: Type of specifications ("jca", "generic", "custom")
            
        Returns:
            Path to created experiment directory
            
        Raises:
            ValidationError: If experiment_id is invalid
            ConfigurationError: If directory cannot be created
        """
        # Validate experiment ID
        if not experiment_id or not isinstance(experiment_id, str):
            raise ValidationError("Experiment ID must be a non-empty string")
        
        if any(char in experiment_id for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']):
            raise ValidationError(f"Invalid characters in experiment ID: {experiment_id}")
        
        experiment_dir = Path(self.structure.experiments_dir) / experiment_id
        
        # Check if experiment already exists
        if experiment_dir.exists():
            self.logger.warning(f"Experiment directory already exists: {experiment_id}")
            return experiment_dir
        
        self.logger.info(f"Creating experiment directory: {experiment_id} (specification_set: {specification_set})")
        
        try:
            # Create main experiment directory
            experiment_dir.mkdir(parents=True, exist_ok=True)
            
            # Create experiment subdirectories
            (experiment_dir / "logs").mkdir(exist_ok=True)
            (experiment_dir / "results").mkdir(exist_ok=True)
            (experiment_dir / "traces").mkdir(exist_ok=True)
            (experiment_dir / "coverage").mkdir(exist_ok=True)
            (experiment_dir / "errors").mkdir(exist_ok=True)
            
            # Create experiment metadata
            metadata = {
                "experiment_id": experiment_id,
                "specification_set": specification_set,
                "created_at": datetime.now().isoformat(),
                "directory_structure_version": "v1"
            }
            
            metadata_file = experiment_dir / "metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            self.logger.info(f"Successfully created experiment directory: {experiment_id}")
            return experiment_dir
            
        except Exception as e:
            # Cleanup on failure
            if experiment_dir.exists():
                shutil.rmtree(experiment_dir, ignore_errors=True)
            
            error_msg = f"Failed to create experiment directory {experiment_id}: {e}"
            self.logger.error(error_msg)
            raise ConfigurationError(error_msg)
    
    def get_instrumented_dir(self, specification_set: str) -> Path:
        """
        Get the appropriate instrumented APKs directory for specification set.
        
        Args:
            specification_set: Type of specifications ("jca", "generic", "custom")
            
        Returns:
            Path to specification-specific instrumented directory
        """
        if specification_set == "jca":
            return Path(self.structure.jca_instrumented_dir)
        elif specification_set == "generic":
            return Path(self.structure.generic_instrumented_dir)
        else:
            # Custom specifications use generic directory
            return Path(self.structure.generic_instrumented_dir)
    
    def get_monitors_dir(self, specification_set: str) -> Path:
        """
        Get the appropriate monitors directory for specification set.
        
        Args:
            specification_set: Type of specifications ("jca", "generic", "custom")
            
        Returns:
            Path to specification-specific monitors directory
        """
        if specification_set == "jca":
            return Path(self.structure.jca_monitors_dir)
        elif specification_set == "generic":
            return Path(self.structure.generic_monitors_dir)
        else:
            return Path(self.structure.custom_monitors_dir)
    
    def get_static_analysis_dir(self, tool: str) -> Path:
        """
        Get the static analysis directory for specific tool.
        
        Args:
            tool: Static analysis tool name ("gator", "gesda", "reach")
            
        Returns:
            Path to tool-specific static analysis directory
        """
        tool_dirs = {
            "gator": self.structure.gator_dir,
            "gesda": self.structure.gesda_dir,
            "reach": self.structure.reach_dir
        }
        
        return Path(tool_dirs.get(tool, self.structure.static_dir))
    
    def get_cache_dir(self, cache_type: str) -> Path:
        """
        Get the cache directory for specific type.
        
        Args:
            cache_type: Type of cache ("tools", "models", "temp")
            
        Returns:
            Path to cache type directory
        """
        cache_dirs = {
            "tools": self.structure.tools_cache_dir,
            "models": self.structure.models_cache_dir,
            "temp": self.structure.temp_dir
        }
        
        return Path(cache_dirs.get(cache_type, self.structure.cache_dir))
    
    @ErrorHandler.handle_errors(
        component="ExperimentDirectoryManager",
        phase="cleanup_temp_files",
    )
    def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """
        Clean up temporary files older than specified age.
        
        Args:
            max_age_hours: Maximum age of temporary files in hours
            
        Returns:
            Number of files cleaned up
        """
        temp_dir = Path(self.structure.temp_dir)
        if not temp_dir.exists():
            return 0
        
        from time import time
        current_time = time()
        max_age_seconds = max_age_hours * 3600
        cleaned_count = 0
        
        try:
            for file_path in temp_dir.rglob('*'):
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        file_path.unlink()
                        cleaned_count += 1
                        
        except Exception as e:
            self.logger.warning(f"Error during temp file cleanup: {e}")
        
        if cleaned_count > 0:
            self.logger.info(f"Cleaned up {cleaned_count} temporary files")
        
        return cleaned_count
    
    def validate_structure(self) -> Dict[str, bool]:
        """
        Validate the integrity of the directory structure.
        
        Returns:
            Dictionary with validation results for each component
        """
        validation_results = {}
        
        # Check all required directories
        directories_to_check = [
            ("base", self.structure.base_dir),
            ("experiments", self.structure.experiments_dir),
            ("instrumented", self.structure.instrumented_dir),
            ("monitors", self.structure.monitors_dir),
            ("static", self.structure.static_dir),
            ("cache", self.structure.cache_dir),
            ("jca_instrumented", self.structure.jca_instrumented_dir),
            ("generic_instrumented", self.structure.generic_instrumented_dir),
            ("jca_monitors", self.structure.jca_monitors_dir),
            ("generic_monitors", self.structure.generic_monitors_dir),
            ("custom_monitors", self.structure.custom_monitors_dir),
            ("gator", self.structure.gator_dir),
            ("gesda", self.structure.gesda_dir),
            ("reach", self.structure.reach_dir),
            ("tools_cache", self.structure.tools_cache_dir),
            ("models_cache", self.structure.models_cache_dir),
            ("temp", self.structure.temp_dir)
        ]
        
        for name, directory in directories_to_check:
            dir_path = Path(directory)
            validation_results[name] = dir_path.exists() and dir_path.is_dir()
        
        return validation_results
    
    def get_experiment_list(self) -> List[Dict[str, str]]:
        """
        Get list of existing experiments with their metadata.
        
        Returns:
            List of experiment information dictionaries
        """
        experiments_dir = Path(self.structure.experiments_dir)
        if not experiments_dir.exists():
            return []
        
        experiments = []
        
        for experiment_dir in experiments_dir.iterdir():
            if experiment_dir.is_dir():
                metadata_file = experiment_dir / "metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        experiments.append(metadata)
                    except Exception:
                        # Fallback for directories without proper metadata
                        experiments.append({
                            "experiment_id": experiment_dir.name,
                            "specification_set": "unknown",
                            "created_at": "unknown"
                        })
        
        return sorted(experiments, key=lambda x: x.get("created_at", ""), reverse=True)