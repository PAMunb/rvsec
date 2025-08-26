"""
Core data models for the RV-Android Test Framework.

This module defines the fundamental data structures used throughout the framework,
leveraging existing rv-android-core models where possible for maximum compatibility.

### Design Principles:
- Reuse existing rv-android-core models (Task, ToolConfig, LLMConfig)
- Simple data structures without complex validation
- User responsibility for data correctness
- Direct conversion to execution objects
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from pydantic import BaseModel, Field


@dataclass
class TestFrameworkConfig:
    """
    Configuration for test framework execution.
    
    Simple configuration object that delegates to existing infrastructure
    without complex validation or resource management logic.
    
    ### User Responsibility:
    - Correct configuration values
    - Appropriate worker count for system capacity
    - Valid APK and configuration paths
    """
    
    # Basic execution parameters
    max_workers: int = 5
    apks_dir: str = "./apks_examples"
    output_dir: str = "./test_framework_results"
    no_window: bool = True
    
    # Configuration and repetition settings
    configurations: List[Dict[str, Any]] = field(default_factory=list)
    repetitions: int = 1
    timeouts: List[int] = field(default_factory=lambda: [300])
    
    # Optional analysis settings
    include_plateau_analysis: bool = True
    
    def get_experiment_name(self) -> str:
        """Generate experiment name with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"test_framework_{timestamp}"


@dataclass 
class TaskResult:
    """
    Result of executing a single task configuration.
    
    Lightweight result object that captures essential execution data
    without complex state management or validation.
    """
    
    # Task identification
    task_id: str
    config_name: str
    apk_name: str
    repetition: int
    
    # Execution results
    success: bool = False
    execution_time: float = 0.0
    error_message: str = ""
    
    # File paths for post-processing
    logcat_file: str = ""
    trace_file: str = ""
    
    # Metrics collected during execution
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization for derived fields."""
        if not self.task_id:
            self.task_id = f"{self.config_name}_{self.apk_name}_{self.repetition}"


@dataclass
class ModelGroup:
    """
    Group of tasks that use the same LLM model.
    
    Simple grouping structure for model-based parallel execution
    without complex resource management or optimization logic.
    """
    
    model_name: str
    model_type: str  # e.g., "ollama", "openai"
    tasks: List[Any] = field(default_factory=list)  # Task objects from rv-android-core
    
    def add_task(self, task: Any) -> None:
        """Add task to this model group."""
        self.tasks.append(task)
    
    def get_task_count(self) -> int:
        """Get number of tasks in this group."""
        return len(self.tasks)


class ExecutionSummary(BaseModel):
    """
    Summary of test framework execution results.
    
    Lightweight summary object for reporting and analysis
    using Pydantic for simple serialization.
    """
    
    # Execution metadata
    start_time: datetime
    end_time: Optional[datetime] = None
    total_execution_time: float = 0.0
    
    # Task statistics
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    success_rate: float = 0.0
    
    # Model group statistics
    total_model_groups: int = 0
    model_transition_count: int = 0
    
    # Resource utilization
    max_workers_used: int = 0
    average_task_time: float = 0.0
    
    # Result file paths
    results_directory: str = ""
    metrics_files: List[str] = Field(default_factory=list)
    report_files: List[str] = Field(default_factory=list)
    
    def calculate_derived_metrics(self) -> None:
        """Calculate derived metrics from basic statistics."""
        if self.total_tasks > 0:
            self.success_rate = self.successful_tasks / self.total_tasks * 100
            self.failed_tasks = self.total_tasks - self.successful_tasks
        
        if self.end_time and self.start_time:
            self.total_execution_time = (self.end_time - self.start_time).total_seconds()
        
        if self.successful_tasks > 0 and self.total_execution_time > 0:
            self.average_task_time = self.total_execution_time / self.successful_tasks


# EmulatorPortAllocation removed - now using dynamic allocation in ParallelManager