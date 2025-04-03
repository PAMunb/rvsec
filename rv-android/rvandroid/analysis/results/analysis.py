# rvandroid/analysis/results/analysis.py
"""
Advanced results analysis system for experiment data.

This module provides comprehensive analysis capabilities for experiment
results, including coverage metrics, error analysis, and performance evaluation.
"""

import json
import os
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Union, TypeVar

from rvandroid.experiment.task.interfaces import TaskState

@dataclass
class TaskResult:
    """Simple task result container."""
    status: TaskState
    execution_time: Optional[float] = None
    coverage_data: Optional[Dict[str, Any]] = None
    errors: Optional[List[Dict[str, Any]]] = None
    performance_data: Optional[Dict[str, Any]] = None
    event_count: Optional[int] = None
    tool_name: str = ""
    app_name: str = ""

@dataclass
class ExperimentResult:
    """Simple experiment result container."""
    experiment_id: str
    task_results: Dict[str, TaskResult] = field(default_factory=dict)


@dataclass
class CoverageMetrics:
    """
    Detailed coverage metrics for experiment analysis.
    
    ### Architectural Decisions:
    - Uses dataclass for type safety and serialization
    - Encapsulates all relevant coverage metrics
    - Provides clear, structured data representation
    - Facilitates consistent metric tracking and reporting
    
    ### Role in the System:
    - Provides a comprehensive view of code coverage
    - Enables detailed coverage analysis and reporting
    - Supports standardized coverage metric representation
    - Facilitates comparison between different tools/apps
    """
    method_coverage: float = 0.0
    activity_coverage: float = 0.0
    mop_method_coverage: float = 0.0
    total_methods: int = 0
    called_methods: int = 0
    total_activities: int = 0
    visited_activities: int = 0
    total_mop_methods: int = 0
    called_mop_methods: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CoverageMetrics':
        """
        Create from dictionary.
        
        Args:
            data: Dictionary data
            
        Returns:
            CoverageMetrics instance
        """
        return cls(**data)
    
    def merge(self, other: 'CoverageMetrics') -> 'CoverageMetrics':
        """
        Merge with another metrics object.
        
        Args:
            other: Metrics to merge with
            
        Returns:
            New merged metrics
        """
        result = CoverageMetrics()
        
        # Sum count fields
        result.total_methods = self.total_methods + other.total_methods
        result.called_methods = self.called_methods + other.called_methods
        result.total_activities = self.total_activities + other.total_activities
        result.visited_activities = self.visited_activities + other.visited_activities
        result.total_mop_methods = self.total_mop_methods + other.total_mop_methods
        result.called_mop_methods = self.called_mop_methods + other.called_mop_methods
        
        # Calculate new coverage percentages
        if result.total_methods > 0:
            result.method_coverage = (result.called_methods / result.total_methods) * 100
            
        if result.total_activities > 0:
            result.activity_coverage = (result.visited_activities / result.total_activities) * 100
            
        if result.total_mop_methods > 0:
            result.mop_method_coverage = (result.called_mop_methods / result.total_mop_methods) * 100
            
        return result


@dataclass
class PerformanceMetrics:
    """
    Performance metrics for experiment analysis.
    
    ### Architectural Decisions:
    - Uses dataclass for type safety and serialization
    - Encapsulates all relevant performance metrics
    - Provides clear, structured data representation
    - Facilitates consistent metric tracking and reporting
    
    ### Role in the System:
    - Provides a comprehensive view of performance characteristics
    - Enables detailed performance analysis and reporting
    - Supports standardized performance metric representation
    - Facilitates comparison between different tools/apps
    """
    execution_time: float = 0.0
    avg_task_time: float = 0.0
    min_task_time: float = 0.0
    max_task_time: float = 0.0
    std_dev_task_time: float = 0.0
    avg_cpu_usage: float = 0.0
    avg_memory_usage: float = 0.0
    peak_cpu_usage: float = 0.0
    peak_memory_usage: float = 0.0
    event_count: int = 0
    events_per_second: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PerformanceMetrics':
        """
        Create from dictionary.
        
        Args:
            data: Dictionary data
            
        Returns:
            PerformanceMetrics instance
        """
        return cls(**data)


@dataclass
class ErrorMetrics:
    """
    Error metrics for experiment analysis.
    
    ### Architectural Decisions:
    - Uses dataclass for type safety and serialization
    - Encapsulates all relevant error metrics
    - Provides clear, structured data representation
    - Facilitates consistent metric tracking and reporting
    
    ### Role in the System:
    - Provides a comprehensive view of error characteristics
    - Enables detailed error analysis and reporting
    - Supports standardized error metric representation
    - Facilitates comparison between different tools/apps
    """
    total_errors: int = 0
    unique_errors: int = 0
    error_categories: Dict[str, int] = field(default_factory=dict)
    error_rate: float = 0.0  # errors per unit time
    app_crash_count: int = 0
    tool_crash_count: int = 0
    system_crash_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ErrorMetrics':
        """
        Create from dictionary.
        
        Args:
            data: Dictionary data
            
        Returns:
            ErrorMetrics instance
        """
        # Handle special fields
        if 'error_categories' in data and isinstance(data['error_categories'], dict):
            error_categories = data['error_categories']
        else:
            error_categories = {}
            
        result = cls(
            total_errors=data.get('total_errors', 0),
            unique_errors=data.get('unique_errors', 0),
            error_categories=error_categories,
            error_rate=data.get('error_rate', 0.0),
            app_crash_count=data.get('app_crash_count', 0),
            tool_crash_count=data.get('tool_crash_count', 0),
            system_crash_count=data.get('system_crash_count', 0)
        )
        
        return result


@dataclass
class AnalysisResult:
    """
    Comprehensive analysis result.
    
    ### Architectural Decisions:
    - Uses dataclass for type safety and serialization
    - Encapsulates all analysis data in a structured format
    - Provides clear, standardized analysis representation
    - Facilitates consistent analysis results across the system
    
    ### Role in the System:
    - Serves as a container for all analysis metrics
    - Enables comprehensive experiment evaluation
    - Supports standardized analysis result representation
    - Facilitates reporting and visualization of results
    """
    experiment_id: str
    coverage: CoverageMetrics
    performance: PerformanceMetrics
    errors: ErrorMetrics
    tools_metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    apps_metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    task_count: int = 0
    completed_task_count: int = 0
    failed_task_count: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return {
            'experiment_id': self.experiment_id,
            'timestamp': self.timestamp,
            'task_count': self.task_count,
            'completed_task_count': self.completed_task_count,
            'failed_task_count': self.failed_task_count,
            'coverage': self.coverage.to_dict(),
            'performance': self.performance.to_dict(),
            'errors': self.errors.to_dict(),
            'tools': self.tools_metrics,
            'apps': self.apps_metrics,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnalysisResult':
        """
        Create from dictionary.
        
        Args:
            data: Dictionary data
            
        Returns:
            AnalysisResult instance
        """
        # Convert component metrics
        coverage = CoverageMetrics.from_dict(data.get('coverage', {}))
        performance = PerformanceMetrics.from_dict(data.get('performance', {}))
        errors = ErrorMetrics.from_dict(data.get('errors', {}))
        
        # Create instance
        return cls(
            experiment_id=data.get('experiment_id', 'unknown'),
            coverage=coverage,
            performance=performance,
            errors=errors,
            tools_metrics=data.get('tools', {}),
            apps_metrics=data.get('apps', {}),
            task_count=data.get('task_count', 0),
            completed_task_count=data.get('completed_task_count', 0),
            failed_task_count=data.get('failed_task_count', 0),
            timestamp=data.get('timestamp', datetime.now().isoformat())
        )
    
    def save_to_file(self, filepath: str) -> None:
        """
        Save analysis result to file.
        
        Args:
            filepath: Path to save to
        """
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'AnalysisResult':
        """
        Load analysis result from file.
        
        Args:
            filepath: Path to load from
            
        Returns:
            AnalysisResult instance
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)


class ResultAnalyzer:
    """
    Advanced analyzer for experiment results.
    
    ### Architectural Decisions:
    - Implements comprehensive analysis for experiment results
    - Provides modular, extensible analysis capabilities
    - Generates standardized metrics and reports
    - Facilitates detailed experiment evaluation
    
    ### Role in the System:
    - Analyzes raw experiment data to generate insights
    - Provides detailed metrics on coverage, performance, and errors
    - Enables comparison between different tools and apps
    - Facilitates experiment evaluation and reporting
    """
    
    def __init__(self, experiment_result: ExperimentResult):
        """
        Initialize the result analyzer.
        
        Args:
            experiment_result: Experiment result to analyze
        """
        self.experiment_result = experiment_result
        self.task_results = experiment_result.task_results
        
    def analyze(self) -> AnalysisResult:
        """
        Perform comprehensive analysis of experiment results.
        
        Returns:
            Analysis result
        """
        # Get metrics
        coverage = self._analyze_coverage()
        performance = self._analyze_performance()
        errors = self._analyze_errors()
        
        # Get tool and app metrics
        tools_metrics = self._analyze_by_tool()
        apps_metrics = self._analyze_by_app()
        
        # Count tasks
        task_count = len(self.task_results)
        completed_task_count = len([
            task for task in self.task_results.values()
            if task.status == TaskState.COMPLETED
        ])
        failed_task_count = len([
            task for task in self.task_results.values()
            if task.status == TaskState.ERROR
        ])
        
        # Create result
        result = AnalysisResult(
            experiment_id=self.experiment_result.experiment_id,
            coverage=coverage,
            performance=performance,
            errors=errors,
            tools_metrics=tools_metrics,
            apps_metrics=apps_metrics,
            task_count=task_count,
            completed_task_count=completed_task_count,
            failed_task_count=failed_task_count
        )
        
        return result
        
    def _analyze_coverage(self) -> CoverageMetrics:
        """
        Analyze coverage data.
        
        Returns:
            Coverage metrics
        """
        # Initialize metrics
        metrics = CoverageMetrics()
        
        # Get completed tasks
        completed_tasks = [
            task for task in self.task_results.values()
            if task.status == TaskState.COMPLETED
        ]
        
        if not completed_tasks:
            return metrics
            
        # Calculate totals
        total_methods = 0
        called_methods = 0
        total_activities = 0
        visited_activities = 0
        total_mop_methods = 0
        called_mop_methods = 0
        
        # Process each task
        for task in completed_tasks:
            # Extract coverage data
            coverage = task.coverage_data or {}
            
            # Update method counts
            total_methods += coverage.get('total_methods', 0)
            called_methods += coverage.get('called_methods', 0)
            
            # Update activity counts
            total_activities += coverage.get('total_activities', 0)
            visited_activities += coverage.get('visited_activities', 0)
            
            # Update MOP method counts
            total_mop_methods += coverage.get('total_mop_methods', 0)
            called_mop_methods += coverage.get('called_mop_methods', 0)
            
        # Set counts
        metrics.total_methods = total_methods
        metrics.called_methods = called_methods
        metrics.total_activities = total_activities
        metrics.visited_activities = visited_activities
        metrics.total_mop_methods = total_mop_methods
        metrics.called_mop_methods = called_mop_methods
        
        # Calculate coverage percentages
        if total_methods > 0:
            metrics.method_coverage = (called_methods / total_methods) * 100
            
        if total_activities > 0:
            metrics.activity_coverage = (visited_activities / total_activities) * 100
            
        if total_mop_methods > 0:
            metrics.mop_method_coverage = (called_mop_methods / total_mop_methods) * 100
            
        return metrics
        
    def _analyze_performance(self) -> PerformanceMetrics:
        """
        Analyze performance data.
        
        Returns:
            Performance metrics
        """
        # Initialize metrics
        metrics = PerformanceMetrics()
        
        # Get completed tasks
        completed_tasks = [
            task for task in self.task_results.values()
            if task.status == TaskState.COMPLETED
        ]
        
        if not completed_tasks:
            return metrics
            
        # Extract execution times
        execution_times = [
            task.execution_time for task in completed_tasks
            if task.execution_time is not None and task.execution_time > 0
        ]
        
        if not execution_times:
            return metrics
            
        # Calculate time metrics
        metrics.execution_time = sum(execution_times)
        metrics.avg_task_time = statistics.mean(execution_times)
        metrics.min_task_time = min(execution_times)
        metrics.max_task_time = max(execution_times)
        
        if len(execution_times) > 1:
            metrics.std_dev_task_time = statistics.stdev(execution_times)
            
        # Extract CPU and memory usage
        cpu_usage = []
        memory_usage = []
        peak_cpu = 0
        peak_memory = 0
        event_count = 0
        
        # Process each task
        for task in completed_tasks:
            # Extract performance data
            perf = task.performance_data or {}
            
            # Update CPU metrics
            cpu_samples = perf.get('cpu_samples', [])
            if cpu_samples:
                avg_cpu = statistics.mean(cpu_samples)
                cpu_usage.append(avg_cpu)
                peak_task_cpu = max(cpu_samples)
                peak_cpu = max(peak_cpu, peak_task_cpu)
                
            # Update memory metrics
            memory_samples = perf.get('memory_samples', [])
            if memory_samples:
                avg_memory = statistics.mean(memory_samples)
                memory_usage.append(avg_memory)
                peak_task_memory = max(memory_samples)
                peak_memory = max(peak_memory, peak_task_memory)
                
            # Update event count
            event_count += task.event_count or 0
            
        # Calculate CPU and memory metrics
        if cpu_usage:
            metrics.avg_cpu_usage = statistics.mean(cpu_usage)
            metrics.peak_cpu_usage = peak_cpu
            
        if memory_usage:
            metrics.avg_memory_usage = statistics.mean(memory_usage)
            metrics.peak_memory_usage = peak_memory
            
        # Calculate event metrics
        metrics.event_count = event_count
        if metrics.execution_time > 0:
            metrics.events_per_second = event_count / metrics.execution_time
            
        return metrics
        
    def _analyze_errors(self) -> ErrorMetrics:
        """
        Analyze error data.
        
        Returns:
            Error metrics
        """
        # Initialize metrics
        metrics = ErrorMetrics()
        
        # Count tasks with errors
        error_tasks = [
            task for task in self.task_results.values()
            if task.status == TaskState.ERROR
        ]
        
        # Initialize error tracking
        total_errors = 0
        unique_errors = set()
        error_categories = {}
        app_crashes = 0
        tool_crashes = 0
        system_crashes = 0
        
        # Process each task
        for task in self.task_results.values():
            # Get errors from task
            errors = task.errors or []
            
            # Process each error
            for error in errors:
                total_errors += 1
                error_text = error.get('message', 'Unknown error')
                unique_errors.add(error_text)
                
                # Categorize error
                category = error.get('category', 'unknown')
                error_categories[category] = error_categories.get(category, 0) + 1
                
                # Count crashes
                if category == 'app_crash':
                    app_crashes += 1
                elif category == 'tool_crash':
                    tool_crashes += 1
                elif category == 'system_crash':
                    system_crashes += 1
                    
        # Set error metrics
        metrics.total_errors = total_errors
        metrics.unique_errors = len(unique_errors)
        metrics.error_categories = error_categories
        metrics.app_crash_count = app_crashes
        metrics.tool_crash_count = tool_crashes
        metrics.system_crash_count = system_crashes
        
        # Calculate error rate
        total_execution_time = sum(
            task.execution_time for task in self.task_results.values()
            if task.execution_time is not None and task.execution_time > 0
        )
        
        if total_execution_time > 0:
            metrics.error_rate = total_errors / total_execution_time
            
        return metrics
        
    def _analyze_by_tool(self) -> Dict[str, Dict[str, Any]]:
        """
        Analyze results by tool.
        
        Returns:
            Tool metrics dictionary
        """
        # Group tasks by tool
        tool_tasks = {}
        
        for task in self.task_results.values():
            tool_name = task.tool_name
            
            if tool_name not in tool_tasks:
                tool_tasks[tool_name] = []
                
            tool_tasks[tool_name].append(task)
            
        # Initialize tool metrics
        tool_metrics = {}
        
        # Process each tool
        for tool_name, tasks in tool_tasks.items():
            # Initialize tool metrics
            metrics = {
                'task_count': len(tasks),
                'completed_count': 0,
                'failed_count': 0,
                'avg_execution_time': 0,
                'coverage': {},
                'errors': 0
            }
            
            # Count completed and failed tasks
            completed_tasks = [task for task in tasks if task.status == TaskState.COMPLETED]
            failed_tasks = [task for task in tasks if task.status == TaskState.ERROR]
            
            metrics['completed_count'] = len(completed_tasks)
            metrics['failed_count'] = len(failed_tasks)
            
            # Calculate average execution time
            execution_times = [
                task.execution_time for task in completed_tasks
                if task.execution_time is not None and task.execution_time > 0
            ]
            
            if execution_times:
                metrics['avg_execution_time'] = statistics.mean(execution_times)
                
            # Calculate coverage metrics
            coverage_metrics = CoverageMetrics()
            
            for task in completed_tasks:
                # Extract coverage data
                coverage = task.coverage_data or {}
                
                # Update method counts
                coverage_metrics.total_methods += coverage.get('total_methods', 0)
                coverage_metrics.called_methods += coverage.get('called_methods', 0)
                
                # Update activity counts
                coverage_metrics.total_activities += coverage.get('total_activities', 0)
                coverage_metrics.visited_activities += coverage.get('visited_activities', 0)
                
                # Update MOP method counts
                coverage_metrics.total_mop_methods += coverage.get('total_mop_methods', 0)
                coverage_metrics.called_mop_methods += coverage.get('called_mop_methods', 0)
                
            # Calculate coverage percentages
            if coverage_metrics.total_methods > 0:
                coverage_metrics.method_coverage = (
                    coverage_metrics.called_methods / coverage_metrics.total_methods
                ) * 100
                
            if coverage_metrics.total_activities > 0:
                coverage_metrics.activity_coverage = (
                    coverage_metrics.visited_activities / coverage_metrics.total_activities
                ) * 100
                
            if coverage_metrics.total_mop_methods > 0:
                coverage_metrics.mop_method_coverage = (
                    coverage_metrics.called_mop_methods / coverage_metrics.total_mop_methods
                ) * 100
                
            metrics['coverage'] = coverage_metrics.to_dict()
            
            # Count errors
            error_count = 0
            for task in tasks:
                errors = task.errors or []
                error_count += len(errors)
                
            metrics['errors'] = error_count
            
            # Add to tool metrics
            tool_metrics[tool_name] = metrics
            
        return tool_metrics
        
    def _analyze_by_app(self) -> Dict[str, Dict[str, Any]]:
        """
        Analyze results by app.
        
        Returns:
            App metrics dictionary
        """
        # Group tasks by app
        app_tasks = {}
        
        for task in self.task_results.values():
            app_name = task.app_name
            
            if app_name not in app_tasks:
                app_tasks[app_name] = []
                
            app_tasks[app_name].append(task)
            
        # Initialize app metrics
        app_metrics = {}
        
        # Process each app
        for app_name, tasks in app_tasks.items():
            # Initialize app metrics
            metrics = {
                'task_count': len(tasks),
                'completed_count': 0,
                'failed_count': 0,
                'avg_execution_time': 0,
                'coverage': {},
                'errors': 0
            }
            
            # Count completed and failed tasks
            completed_tasks = [task for task in tasks if task.status == TaskState.COMPLETED]
            failed_tasks = [task for task in tasks if task.status == TaskState.ERROR]
            
            metrics['completed_count'] = len(completed_tasks)
            metrics['failed_count'] = len(failed_tasks)
            
            # Calculate average execution time
            execution_times = [
                task.execution_time for task in completed_tasks
                if task.execution_time is not None and task.execution_time > 0
            ]
            
            if execution_times:
                metrics['avg_execution_time'] = statistics.mean(execution_times)
                
            # Calculate coverage metrics
            coverage_metrics = CoverageMetrics()
            
            for task in completed_tasks:
                # Extract coverage data
                coverage = task.coverage_data or {}
                
                # Update method counts
                coverage_metrics.total_methods += coverage.get('total_methods', 0)
                coverage_metrics.called_methods += coverage.get('called_methods', 0)
                
                # Update activity counts
                coverage_metrics.total_activities += coverage.get('total_activities', 0)
                coverage_metrics.visited_activities += coverage.get('visited_activities', 0)
                
                # Update MOP method counts
                coverage_metrics.total_mop_methods += coverage.get('total_mop_methods', 0)
                coverage_metrics.called_mop_methods += coverage.get('called_mop_methods', 0)
                
            # Calculate coverage percentages
            if coverage_metrics.total_methods > 0:
                coverage_metrics.method_coverage = (
                    coverage_metrics.called_methods / coverage_metrics.total_methods
                ) * 100
                
            if coverage_metrics.total_activities > 0:
                coverage_metrics.activity_coverage = (
                    coverage_metrics.visited_activities / coverage_metrics.total_activities
                ) * 100
                
            if coverage_metrics.total_mop_methods > 0:
                coverage_metrics.mop_method_coverage = (
                    coverage_metrics.called_mop_methods / coverage_metrics.total_mop_methods
                ) * 100
                
            metrics['coverage'] = coverage_metrics.to_dict()
            
            # Count errors
            error_count = 0
            for task in tasks:
                errors = task.errors or []
                error_count += len(errors)
                
            metrics['errors'] = error_count
            
            # Add to app metrics
            app_metrics[app_name] = metrics
            
        return app_metrics