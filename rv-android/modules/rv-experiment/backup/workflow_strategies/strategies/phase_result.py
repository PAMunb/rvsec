"""
Phase Execution Result Models

This module defines structured result models for phase execution in the
experiment workflow, providing type-safe data structures for tracking
execution outcomes, performance metrics, and fallback scenarios.

### Key Classes:
- PhaseResult: Main result data structure for phase execution
- PhaseExecutionMode: Enum for execution mode tracking
- PhaseArtifacts: Artifact management data

### Architecture Benefits:
- Type-safe result handling
- Structured performance tracking
- Clear fallback mode indication
- Artifact management integration
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import List, Optional, Dict, Any

from rv_android_core.util.validation import BaseValidatedModel
from rv_android_core.util.error.error_handler import ErrorHandler
from pydantic import Field


class PhaseExecutionMode(Enum):
    """Enumeration of phase execution modes."""
    FULL = "full"
    FALLBACK = "fallback"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class PhaseArtifacts:
    """
    Phase artifact tracking data.
    
    ### Artifact Management:
    - created: New artifacts generated during execution
    - reused: Existing artifacts reused from previous runs
    - validated: Artifacts validated for integrity
    - failed_validation: Artifacts that failed validation
    """
    created: List[str] = field(default_factory=list)
    reused: List[str] = field(default_factory=list)
    validated: List[str] = field(default_factory=list)
    failed_validation: List[str] = field(default_factory=list)

    @property
    def total_artifacts(self) -> int:
        """Total number of artifacts managed."""
        return len(self.created) + len(self.reused)

    @property
    def has_failures(self) -> bool:
        """Check if any artifacts failed validation."""
        return len(self.failed_validation) > 0


@dataclass
class PhaseResult:
    """
    Structured result data for phase execution.
    
    ### Result Structure:
    - Execution status and mode tracking
    - Performance metrics and timing
    - Artifact management information
    - Error context and fallback reasons
    - Continuation control for workflow
    
    ### Architecture Integration:
    - Works with Strategy Pattern for flexible execution
    - Provides rich context for debugging and monitoring
    - Enables graceful workflow continuation decisions
    - Supports artifact reuse detection and validation
    """
    success: bool
    phase_name: str
    execution_mode: PhaseExecutionMode
    can_continue: bool
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    artifacts: PhaseArtifacts = field(default_factory=PhaseArtifacts)
    fallback_reason: Optional[str] = None
    error_context: Optional[Dict[str, Any]] = None
    performance_metrics: Optional[Dict[str, float]] = None
    
    @property
    def execution_time(self) -> Optional[float]:
        """Calculate execution time in seconds."""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def is_degraded(self) -> bool:
        """Check if execution was in degraded/fallback mode."""
        return self.execution_mode in [PhaseExecutionMode.FALLBACK, PhaseExecutionMode.SKIPPED]
    
    @property
    def has_artifacts(self) -> bool:
        """Check if any artifacts were managed."""
        return self.artifacts.total_artifacts > 0
    
    def mark_completed(self, success: bool = True) -> None:
        """Mark phase execution as completed."""
        self.end_time = datetime.now()
        self.success = success
    
    def add_artifact(self, artifact_path: str, artifact_type: str = "created") -> None:
        """Add artifact to appropriate tracking list."""
        if artifact_type == "created":
            self.artifacts.created.append(artifact_path)
        elif artifact_type == "reused":
            self.artifacts.reused.append(artifact_path)
        elif artifact_type == "validated":
            self.artifacts.validated.append(artifact_path)
        elif artifact_type == "failed_validation":
            self.artifacts.failed_validation.append(artifact_path)
    
    def set_fallback_mode(self, reason: str) -> None:
        """Set execution mode to fallback with reason."""
        self.execution_mode = PhaseExecutionMode.FALLBACK
        self.fallback_reason = reason
    
    def add_performance_metric(self, metric_name: str, value: float) -> None:
        """Add performance metric to tracking."""
        if self.performance_metrics is None:
            self.performance_metrics = {}
        self.performance_metrics[metric_name] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "success": self.success,
            "phase_name": self.phase_name,
            "execution_mode": self.execution_mode.value,
            "can_continue": self.can_continue,
            "execution_time": self.execution_time,
            "artifacts": {
                "created": self.artifacts.created,
                "reused": self.artifacts.reused,
                "validated": self.artifacts.validated,
                "failed_validation": self.artifacts.failed_validation,
                "total": self.artifacts.total_artifacts
            },
            "fallback_reason": self.fallback_reason,
            "error_context": self.error_context,
            "performance_metrics": self.performance_metrics,
            "is_degraded": self.is_degraded
        }


class PhaseExecutionContext(BaseValidatedModel):
    """
    Execution context for phase strategies.
    
    ### Context Data:
    - Configuration references and settings
    - Resource availability information
    - Artifact validation results
    - Performance monitoring setup
    """
    experiment_config: Any = Field(..., description="Experiment configuration instance")
    phase_name: str = Field(..., description="Name of phase being executed")
    force_execution: bool = Field(default=False, description="Force execution even if artifacts exist")
    validate_artifacts: bool = Field(default=True, description="Enable artifact validation")
    enable_fallback: bool = Field(default=True, description="Enable fallback mode on failures")
    artifact_directories: Dict[str, str] = Field(default_factory=dict, description="Directory mappings for artifacts")
    resource_constraints: Optional[Dict[str, Any]] = Field(default=None, description="Resource availability constraints")
    
    def get_artifact_dir(self, artifact_type: str) -> Optional[str]:
        """Get directory path for specific artifact type."""
        return self.artifact_directories.get(artifact_type)
    
    def has_resource_constraint(self, resource_name: str) -> bool:
        """Check if specific resource constraint exists."""
        if not self.resource_constraints:
            return False
        return resource_name in self.resource_constraints