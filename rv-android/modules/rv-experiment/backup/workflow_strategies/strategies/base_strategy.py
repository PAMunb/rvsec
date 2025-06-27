"""
Base Phase Execution Strategy

This module defines the abstract base class for phase execution strategies
in the RV-Android experiment workflow system, establishing the contract
for strategy implementations and common functionality.

### Strategy Pattern Implementation:
- Abstract interface for phase execution
- Common validation and artifact management
- Error handling and logging integration
- Event publishing for workflow coordination

### Architecture Benefits:
- Consistent execution interface across strategies
- Pluggable execution strategies for different scenarios
- Centralized common functionality
- Type-safe strategy contracts
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import os
from pathlib import Path

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.exceptions import RVExperimentError

from .phase_result import PhaseResult, PhaseExecutionMode, PhaseExecutionContext, PhaseArtifacts


class PhaseExecutionStrategy(ABC):
    """
    Abstract base class for phase execution strategies.
    
    ### Strategy Pattern Architecture:
    - Defines common interface for all execution strategies
    - Provides shared functionality for artifact validation
    - Implements error handling and logging patterns
    - Establishes workflow coordination protocols
    
    ### Key Responsibilities:
    - Execute phases with strategy-specific behavior
    - Validate artifacts and manage reuse
    - Handle errors with appropriate fallback logic
    - Publish events for workflow coordination
    - Provide rich context for debugging
    """
    
    def __init__(self, config: Any, logger_name: str = "PhaseExecutionStrategy"):
        """
        Initialize strategy with configuration and logging.
        
        Args:
            config: Experiment configuration instance
            logger_name: Name for logger context
        """
        self.config = config
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            f"rv_experiment.workflow.strategies.{logger_name}",
            {CONTEXT_COMPONENT: logger_name}
        )
        
        # Initialize strategy state
        self.execution_history: Dict[str, PhaseResult] = {}
        self.artifact_cache: Dict[str, List[str]] = {}
        
        self.logger.info(f"Initialized {self.__class__.__name__}")
    
    @abstractmethod
    def execute_phase(self, context: PhaseExecutionContext) -> PhaseResult:
        """
        Execute a specific phase with strategy-specific behavior.
        
        ### Strategy Contract:
        - Each strategy must implement its own execution logic
        - Must return structured PhaseResult for workflow coordination
        - Should handle failures according to strategy policy
        - Must update execution context and publish events
        
        Args:
            context: Phase execution context with configuration and constraints
            
        Returns:
            Structured result indicating execution outcome and artifacts
            
        Raises:
            RVExperimentError: For critical failures that prevent continuation
        """
        pass
    
    @ErrorHandler.handle_errors(
        component="PhaseExecutionStrategy",
        phase="artifact_validation"
    )
    def validate_artifacts(self, artifact_dir: str, artifact_patterns: List[str]) -> Dict[str, bool]:
        """
        Validate artifacts in directory against expected patterns.
        
        ### Validation Strategy:
        - Check file existence and accessibility
        - Validate file sizes and basic integrity
        - Cache validation results for performance
        - Provide detailed validation context
        
        Args:
            artifact_dir: Directory containing artifacts to validate
            artifact_patterns: List of file patterns to check (e.g., ['*.rvm', '*.aj'])
            
        Returns:
            Dictionary mapping artifact patterns to validation status
        """
        validation_results = {}
        
        if not os.path.exists(artifact_dir):
            self.logger.warning(f"Artifact directory does not exist: {artifact_dir}")
            return {pattern: False for pattern in artifact_patterns}
        
        for pattern in artifact_patterns:
            pattern_files = list(Path(artifact_dir).glob(pattern))
            pattern_valid = len(pattern_files) > 0
            
            if pattern_valid:
                # Validate file accessibility and basic integrity
                for file_path in pattern_files:
                    if not file_path.is_file() or file_path.stat().st_size == 0:
                        pattern_valid = False
                        break
            
            validation_results[pattern] = pattern_valid
            
            if pattern_valid:
                self.logger.debug(f"Artifact pattern '{pattern}' validated: {len(pattern_files)} files")
            else:
                self.logger.warning(f"Artifact pattern '{pattern}' validation failed")
        
        return validation_results
    
    @ErrorHandler.handle_errors(
        component="PhaseExecutionStrategy",
        phase="directory_preparation"
    )
    def prepare_output_directory(self, output_dir: str, clean_existing: bool = False) -> bool:
        """
        Prepare output directory for phase execution.
        
        ### Directory Management:
        - Create directory structure if missing
        - Optionally clean existing contents
        - Validate directory permissions
        - Log directory preparation actions
        
        Args:
            output_dir: Target output directory path
            clean_existing: Whether to clean existing directory contents
            
        Returns:
            True if directory prepared successfully
            
        Raises:
            RVExperimentError: If directory preparation fails
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Clean existing contents if requested
            if clean_existing and os.path.exists(output_dir):
                import shutil
                for item in os.listdir(output_dir):
                    item_path = os.path.join(output_dir, item)
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                self.logger.info(f"Cleaned existing directory: {output_dir}")
            
            # Validate directory permissions
            if not os.access(output_dir, os.W_OK):
                raise RVExperimentError(f"No write permission for directory: {output_dir}")
            
            self.logger.debug(f"Output directory prepared: {output_dir}")
            return True
            
        except Exception as e:
            raise RVExperimentError(f"Failed to prepare output directory {output_dir}: {e}")
    
    def get_execution_history(self, phase_name: str) -> Optional[PhaseResult]:
        """Get previous execution result for a phase."""
        return self.execution_history.get(phase_name)
    
    def record_execution(self, result: PhaseResult) -> None:
        """Record phase execution result in history."""
        self.execution_history[result.phase_name] = result
        self.logger.debug(f"Recorded execution for phase: {result.phase_name}")
    
    def cache_artifacts(self, phase_name: str, artifacts: List[str]) -> None:
        """Cache artifact list for a phase."""
        self.artifact_cache[phase_name] = artifacts
        self.logger.debug(f"Cached {len(artifacts)} artifacts for phase: {phase_name}")
    
    def get_cached_artifacts(self, phase_name: str) -> List[str]:
        """Get cached artifacts for a phase."""
        return self.artifact_cache.get(phase_name, [])
    
    @ErrorHandler.handle_errors(
        component="PhaseExecutionStrategy",
        phase="result_creation"
    )
    def create_result(self, 
                     phase_name: str, 
                     success: bool, 
                     execution_mode: PhaseExecutionMode,
                     can_continue: bool = True) -> PhaseResult:
        """
        Create standardized PhaseResult instance.
        
        ### Result Factory:
        - Standardized result creation across strategies
        - Consistent field initialization
        - Error context preparation
        - Performance metric initialization
        
        Args:
            phase_name: Name of the executed phase
            success: Whether execution was successful
            execution_mode: Mode of execution (full, fallback, skipped)
            can_continue: Whether workflow can continue after this result
            
        Returns:
            Initialized PhaseResult instance
        """
        result = PhaseResult(
            success=success,
            phase_name=phase_name,
            execution_mode=execution_mode,
            can_continue=can_continue
        )
        
        self.logger.debug(f"Created result for phase {phase_name}: {execution_mode.value}")
        return result
    
    def log_execution_summary(self, result: PhaseResult) -> None:
        """Log comprehensive execution summary."""
        mode_indicator = "🔄" if result.is_degraded else "✅"
        
        self.logger.info(
            f"{mode_indicator} Phase '{result.phase_name}' completed: "
            f"mode={result.execution_mode.value}, "
            f"success={result.success}, "
            f"artifacts={result.artifacts.total_artifacts}, "
            f"time={result.execution_time:.2f}s" if result.execution_time else "time=N/A"
        )
        
        if result.fallback_reason:
            self.logger.warning(f"Fallback reason: {result.fallback_reason}")
        
        if result.artifacts.has_failures:
            self.logger.warning(f"Artifact validation failures: {len(result.artifacts.failed_validation)}")