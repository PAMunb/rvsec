"""
Integrated metrics module for combining static analysis and runtime data.

This module provides classes for integrating static analysis information with
runtime coverage data, enabling comprehensive metrics for instrumented apps.
"""

import json
import os
import statistics
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Union, TypeVar

from rvandroid.analysis.results.analysis import CoverageMetrics, ErrorMetrics, PerformanceMetrics
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.domain.coverage import LogcatRepository


@dataclass
class StaticAnalysisMetrics:
    """
    Metrics derived from static analysis data.
    
    Provides structured metrics about the application's static characteristics,
    including component counts, method counts, and security-relevant information.
    """
    total_classes: int = 0
    total_methods: int = 0
    total_activities: int = 0
    total_services: int = 0
    total_receivers: int = 0
    total_providers: int = 0
    total_mop_methods: int = 0
    total_windows: int = 0
    total_transitions: int = 0
    mop_specifications: int = 0
    security_methods: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for serialization."""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StaticAnalysisMetrics':
        """Create from dictionary."""
        # Handle special fields
        if 'security_methods' in data and isinstance(data['security_methods'], dict):
            security_methods = data['security_methods']
        else:
            security_methods = {}
            
        return cls(
            total_classes=data.get('total_classes', 0),
            total_methods=data.get('total_methods', 0),
            total_activities=data.get('total_activities', 0),
            total_services=data.get('total_services', 0),
            total_receivers=data.get('total_receivers', 0),
            total_providers=data.get('total_providers', 0),
            total_mop_methods=data.get('total_mop_methods', 0),
            total_windows=data.get('total_windows', 0),
            total_transitions=data.get('total_transitions', 0),
            mop_specifications=data.get('mop_specifications', 0),
            security_methods=security_methods
        )


@dataclass
class IntegratedCoverageMetrics:
    """
    Integrated coverage metrics combining static and runtime data.
    
    Extends standard coverage metrics with detailed information about
    security-relevant coverage and runtime behavior.
    """
    # Standard coverage metrics
    method_coverage: float = 0.0
    activity_coverage: float = 0.0
    mop_method_coverage: float = 0.0
    total_methods: int = 0
    called_methods: int = 0
    total_activities: int = 0
    visited_activities: int = 0
    total_mop_methods: int = 0
    called_mop_methods: int = 0
    
    # Enhanced coverage metrics
    security_method_coverage: float = 0.0
    window_coverage: float = 0.0
    transition_coverage: float = 0.0
    total_security_methods: int = 0
    called_security_methods: int = 0
    total_windows: int = 0
    visited_windows: int = 0
    total_transitions: int = 0
    traversed_transitions: int = 0
    
    # Lists of covered elements
    covered_methods: List[str] = field(default_factory=list)
    covered_activities: List[str] = field(default_factory=list)
    covered_mop_methods: List[str] = field(default_factory=list)
    covered_security_methods: List[str] = field(default_factory=list)
    visited_windows_list: List[str] = field(default_factory=list)
    traversed_transitions_list: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IntegratedCoverageMetrics':
        """Create from dictionary."""
        return cls(**data)
    
    @classmethod
    def from_coverage_metrics(cls, coverage: CoverageMetrics) -> 'IntegratedCoverageMetrics':
        """Create from basic coverage metrics."""
        # Get attributes safely with default values
        coverage_dict = coverage.to_dict() if hasattr(coverage, 'to_dict') else {}
        
        # Get values with defaults
        method_coverage = coverage_dict.get("method_coverage", 0)
        activity_coverage = coverage_dict.get("activity_coverage", 0)
        mop_method_coverage = coverage_dict.get("mop_method_coverage", 0)
        
        # Direct attributes
        total_methods = getattr(coverage, "total_methods", 0)
        called_methods = getattr(coverage, "called_methods", 0)
        total_activities = getattr(coverage, "total_activities", 0)
        called_activities = getattr(coverage, "called_activities", 0)
        total_mop_methods = getattr(coverage, "total_mop_methods", 0)
        called_mop_methods = getattr(coverage, "called_mop_methods", 0)
        
        return cls(
            method_coverage=method_coverage,
            activity_coverage=activity_coverage,
            mop_method_coverage=mop_method_coverage,
            total_methods=total_methods,
            called_methods=called_methods,
            total_activities=total_activities,
            visited_activities=called_activities,  # visits == calls in this context
            total_mop_methods=total_mop_methods,
            called_mop_methods=called_mop_methods
        )


@dataclass
class MonitoredOperationsMetrics:
    """
    Metrics for monitored operations in application analysis.
    
    Captures detailed metrics about operations being monitored by specifications,
    including MOP specifications, violations, and patterns of monitored behavior.
    
    This class represents metrics for operations that are being monitored by
    any type of specification, not limited to security specifications.
    """
    # MOP specification metrics
    mop_specifications: int = 0
    mop_triggers: int = 0
    triggered_specifications: Set[str] = field(default_factory=set)
    
    # Specification categories
    spec_categories: Dict[str, int] = field(default_factory=dict)
    
    # Operation monitoring
    monitored_operations_count: int = 0
    monitored_operations_triggered: int = 0
    
    # Detailed specification data
    spec_trigger_count: Dict[str, int] = field(default_factory=dict)
    spec_operation_map: Dict[str, List[str]] = field(default_factory=dict)
    
    # Pattern analysis
    operation_sequence_patterns: Dict[str, int] = field(default_factory=dict)
    common_violation_contexts: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        # Convert sets to lists for JSON serialization
        if 'triggered_specifications' in data:
            data['triggered_specifications'] = list(data['triggered_specifications'])
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MonitoredOperationsMetrics':
        """Create from dictionary."""
        # Handle special fields
        if 'triggered_specifications' in data and isinstance(data['triggered_specifications'], list):
            triggered_specifications = set(data['triggered_specifications'])
        else:
            triggered_specifications = set()
            
        if 'spec_categories' in data and isinstance(data['spec_categories'], dict):
            spec_categories = data['spec_categories']
        else:
            spec_categories = {}
            
        if 'spec_trigger_count' in data and isinstance(data['spec_trigger_count'], dict):
            spec_trigger_count = data['spec_trigger_count']
        else:
            spec_trigger_count = {}
            
        if 'spec_operation_map' in data and isinstance(data['spec_operation_map'], dict):
            spec_operation_map = data['spec_operation_map']
        else:
            spec_operation_map = {}
            
        if 'operation_sequence_patterns' in data and isinstance(data['operation_sequence_patterns'], dict):
            operation_sequence_patterns = data['operation_sequence_patterns']
        else:
            operation_sequence_patterns = {}
            
        if 'common_violation_contexts' in data and isinstance(data['common_violation_contexts'], dict):
            common_violation_contexts = data['common_violation_contexts']
        else:
            common_violation_contexts = {}
            
        return cls(
            mop_specifications=data.get('mop_specifications', 0),
            mop_triggers=data.get('mop_triggers', 0),
            triggered_specifications=triggered_specifications,
            spec_categories=spec_categories,
            monitored_operations_count=data.get('monitored_operations_count', 0),
            monitored_operations_triggered=data.get('monitored_operations_triggered', 0),
            spec_trigger_count=spec_trigger_count,
            spec_operation_map=spec_operation_map,
            operation_sequence_patterns=operation_sequence_patterns,
            common_violation_contexts=common_violation_contexts
        )
        
    def get_monitored_operations_ratio(self) -> float:
        """
        Calculate the ratio of triggered monitored operations.
        
        Returns:
            Ratio as a percentage (0-100)
        """
        if self.monitored_operations_count > 0:
            return (self.monitored_operations_triggered / self.monitored_operations_count) * 100
        return 0.0


@dataclass
class IntegratedAnalysisResult:
    """
    Comprehensive integrated analysis result.
    
    Combines static analysis metrics, runtime coverage, monitored operations metrics,
    and error data into a unified analysis result for a complete view of the application.
    
    This class provides a holistic representation of an application's behavior,
    including its structure, runtime coverage, monitored operations violations,
    and overall performance characteristics.
    """
    app_id: str
    static_metrics: StaticAnalysisMetrics
    coverage: IntegratedCoverageMetrics
    monitored_operations: MonitoredOperationsMetrics
    performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    errors: ErrorMetrics = field(default_factory=ErrorMetrics)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            Dictionary with all metrics for serialization
        """
        return {
            'app_id': self.app_id,
            'timestamp': self.timestamp,
            'static_metrics': self.static_metrics.to_dict(),
            'coverage': self.coverage.to_dict(),
            'monitored_operations': self.monitored_operations.to_dict(),
            'performance': self.performance.to_dict(),
            'errors': self.errors.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IntegratedAnalysisResult':
        """
        Create from dictionary.
        
        Args:
            data: Dictionary with serialized analysis data
            
        Returns:
            IntegratedAnalysisResult instance
        """
        # Convert component metrics
        static_metrics = StaticAnalysisMetrics.from_dict(data.get('static_metrics', {}))
        coverage = IntegratedCoverageMetrics.from_dict(data.get('coverage', {}))
        
        # Handle backward compatibility for security -> monitored_operations
        if 'monitored_operations' in data:
            monitored_operations = MonitoredOperationsMetrics.from_dict(data.get('monitored_operations', {}))
        elif 'security' in data:
            # Convert legacy security metrics to monitored operations
            security_data = data.get('security', {})
            monitored_data = {
                'mop_specifications': security_data.get('mop_specifications', 0),
                'mop_triggers': security_data.get('mop_triggers', 0),
                'triggered_specifications': security_data.get('triggered_specifications', []),
                'spec_categories': security_data.get('vulnerability_categories', {})
            }
            monitored_operations = MonitoredOperationsMetrics.from_dict(monitored_data)
        else:
            monitored_operations = MonitoredOperationsMetrics()
            
        performance = PerformanceMetrics.from_dict(data.get('performance', {}))
        errors = ErrorMetrics.from_dict(data.get('errors', {}))
        
        # Create instance
        return cls(
            app_id=data.get('app_id', 'unknown'),
            static_metrics=static_metrics,
            coverage=coverage,
            monitored_operations=monitored_operations,
            performance=performance,
            errors=errors,
            timestamp=data.get('timestamp', datetime.now().isoformat())
        )
    
    def save_to_file(self, filepath: str) -> None:
        """Save analysis result to file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'IntegratedAnalysisResult':
        """Load analysis result from file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)


class IntegratedMetricsCalculator:
    """
    Calculator for integrated metrics.
    
    Processes both static analysis data and runtime coverage data to generate
    comprehensive integrated metrics for instrumented applications.
    """
    
    def __init__(self, app_id: str):
        """
        Initialize the calculator.
        
        Args:
            app_id: Identifier for the application
        """
        self.app_id = app_id
        self.static_data = None
        self.logcat_data = None
        self.logger = logging.getLogger(__name__)
        
    def set_static_data(self, static_data: StaticAnalysisData) -> None:
        """
        Set static analysis data.
        
        Args:
            static_data: Static analysis data from GESDA, GATOR, etc.
        """
        self.static_data = static_data
        
        # Log information about the static data
        if static_data:
            classes_count = len(static_data.classes.classes) if static_data.classes else 0
            windows_count = len(static_data.windows.windows) if static_data.windows else 0
            wtg_count = len(static_data.wtg.transitions) if (static_data.wtg and hasattr(static_data.wtg, 'transitions')) else 0
            
            self.logger.info(f"Static data set in calculator: classes={classes_count}, "
                           f"windows={windows_count}, transitions={wtg_count}")
        else:
            self.logger.warning("Received None static_data in calculator")
        
    def set_logcat_data(self, logcat_data: LogcatRepository) -> None:
        """
        Set logcat repository data.
        
        Args:
            logcat_data: Logcat repository with runtime coverage data
        """
        self.logcat_data = logcat_data
        
    def calculate_metrics(self) -> IntegratedAnalysisResult:
        """
        Calculate integrated metrics from available data.
        
        This method orchestrates the calculation of all metrics categories
        including static metrics, coverage metrics, monitored operations metrics,
        and error data, then combines them into a comprehensive result.
        
        Returns:
            IntegratedAnalysisResult with comprehensive metrics
        """
        self.logger.info(f"Calculating integrated metrics for {self.app_id}")
        self.logger.info(f"Static data available: {bool(self.static_data)}")
        self.logger.info(f"Logcat data available: {bool(self.logcat_data)}")
        
        # Initialize metrics
        static_metrics = self._calculate_static_metrics()
        coverage_metrics = self._calculate_coverage_metrics()
        monitored_ops_metrics = self._calculate_monitored_operations_metrics()
        
        # Initialize error metrics
        error_metrics = ErrorMetrics()
        
        # Populate error metrics from monitored operations data
        if self.logcat_data and hasattr(self.logcat_data, 'errors'):
            error_metrics.total_errors = len(self.logcat_data.errors)
            
            # Track MOP-specific errors
            mop_errors = []
            mop_error_types = {}
            mop_specs_triggered = []
            mop_specs_triggered_counts = {}
            
            # Populate MOP error data
            for error in self.logcat_data.errors:
                if hasattr(error, 'spec') and error.spec:
                    mop_errors.append(error)
                    mop_specs_triggered.append(error.spec)
                    
                    # Count occurrences of each specification
                    mop_specs_triggered_counts[error.spec] = mop_specs_triggered_counts.get(error.spec, 0) + 1
                    
                    # Count error types
                    if hasattr(error, 'error_type') and error.error_type:
                        error_type = error.error_type
                        mop_error_types[error_type] = mop_error_types.get(error_type, 0) + 1
            
            # Update error metrics
            error_metrics.mop_error_count = len(mop_errors)
            error_metrics.mop_unique_errors = len(set(mop_specs_triggered))
            error_metrics.mop_error_categories = mop_error_types
            error_metrics.mop_specs_triggered = list(set(mop_specs_triggered))
            error_metrics.mop_specs_triggered_counts = mop_specs_triggered_counts
            
            # Transfer monitoring metrics
            error_metrics.monitored_operations_count = monitored_ops_metrics.monitored_operations_count
            error_metrics.monitored_operations_triggered = monitored_ops_metrics.monitored_operations_triggered
            error_metrics.update_monitored_operations_ratio()
            
            # Calculate error rate if execution time is available
            if hasattr(self.logcat_data, 'execution_time') and self.logcat_data.execution_time > 0:
                error_metrics.error_rate = error_metrics.total_errors / self.logcat_data.execution_time
                error_metrics.mop_error_rate = error_metrics.mop_error_count / self.logcat_data.execution_time
        
        # Create result
        result = IntegratedAnalysisResult(
            app_id=self.app_id,
            static_metrics=static_metrics,
            coverage=coverage_metrics,
            monitored_operations=monitored_ops_metrics,
            performance=PerformanceMetrics(),  # Default performance metrics
            errors=error_metrics
        )
        
        return result
    
    def _calculate_static_metrics(self) -> StaticAnalysisMetrics:
        """
        Calculate static analysis metrics.
        
        Returns:
            StaticAnalysisMetrics containing static analysis information
        """
        metrics = StaticAnalysisMetrics()
        
        # If no static data available, return empty metrics
        if not self.static_data:
            return metrics
            
        # Extract metrics from static data
        classes = self.static_data.classes
        windows = self.static_data.windows
        wtg = self.static_data.wtg
        
        # Count classes and methods
        metrics.total_classes = len(classes.classes)
        metrics.total_methods = sum(
            len(cls.methods) for cls in classes.classes.values()
        )
        
        # Count components
        metrics.total_activities = sum(
            1 for cls in classes.classes.values() if getattr(cls, 'is_activity', False)
        )
        metrics.total_services = sum(
            1 for cls in classes.classes.values() if getattr(cls, 'is_service', False)
        )
        metrics.total_receivers = sum(
            1 for cls in classes.classes.values() if getattr(cls, 'is_receiver', False)
        )
        metrics.total_providers = sum(
            1 for cls in classes.classes.values() if getattr(cls, 'is_provider', False)
        )
        
        # Count MOP methods
        metrics.total_mop_methods = sum(
            1 for cls in classes.classes.values()
            for method in cls.methods  # methods is a Set, not a Dict
            if hasattr(method, 'reaches_mop') and method.reaches_mop
        )
        
        # Count windows and transitions
        metrics.total_windows = len(windows.windows) if windows else 0
        # WindowTransitionGraph doesn't have 'edges' attribute directly, it has 'transitions'
        metrics.total_transitions = len(wtg.transitions) if wtg and hasattr(wtg, 'transitions') else 0
        
        # Count MOP specifications
        mop_specs = set()
        for cls in classes.classes.values():
            # methods is a Set, not a Dict
            for method in cls.methods:
                if (hasattr(method, 'reaches_mop') and method.reaches_mop and 
                    hasattr(method, 'mop_specs') and method.mop_specs):
                    mop_specs.update(method.mop_specs)
        metrics.mop_specifications = len(mop_specs)
        
        # Count security methods by category
        security_methods = {}
        for cls in classes.classes.values():
            # methods is a Set, not a Dict
            for method in cls.methods:
                if (hasattr(method, 'reaches_mop') and method.reaches_mop and 
                    hasattr(method, 'mop_specs') and method.mop_specs):
                    for spec in method.mop_specs:
                        category = spec.split('.')[0] if '.' in spec else spec
                        security_methods[category] = security_methods.get(category, 0) + 1
        metrics.security_methods = security_methods
        
        return metrics
    
    def _calculate_coverage_metrics(self) -> IntegratedCoverageMetrics:
        """
        Calculate integrated coverage metrics.
        
        Returns:
            IntegratedCoverageMetrics combining static and runtime data
        """
        metrics = IntegratedCoverageMetrics()
        
        # If no data available, return empty metrics
        if not self.static_data and not self.logcat_data:
            return metrics
            
        # Start with basic coverage metrics if logcat data is available
        if self.logcat_data:
            basic_metrics = self.logcat_data.calculate_metrics()
            metrics = IntegratedCoverageMetrics.from_coverage_metrics(basic_metrics)
            
            # Extract detailed lists if possible
            if hasattr(self.logcat_data, "classes"):
                covered_methods = []
                covered_activities = []
                covered_mop_methods = []
                
                for class_name, class_obj in self.logcat_data.classes.items():
                    is_activity = class_obj.is_activity
                    
                    for method_name, method_obj in class_obj.methods.items():
                        if method_obj.called:
                            method_id = f"{class_name}.{method_name}"
                            covered_methods.append(method_id)
                            
                            if is_activity:
                                covered_activities.append(method_id)
                                
                            if method_obj.reaches_mop:
                                covered_mop_methods.append(method_id)
                
                metrics.covered_methods = covered_methods
                metrics.covered_activities = covered_activities
                metrics.covered_mop_methods = covered_mop_methods
        
        # No static data, so we're done
        if not self.static_data:
            return metrics
            
        # Enhance with static data when available
        static_data = self.static_data
        
        # Set total methods and activities if not already set
        if metrics.total_methods == 0:
            metrics.total_methods = sum(
                len(cls.methods) for cls in static_data.classes.classes.values()
            )
            
        if metrics.total_activities == 0:
            metrics.total_activities = sum(
                1 for cls in static_data.classes.classes.values() if cls.is_activity
            )
            
        if metrics.total_mop_methods == 0:
            metrics.total_mop_methods = sum(
                1 for cls in static_data.classes.classes.values()
                for method in cls.methods  # methods is a Set, not a Dict
                if hasattr(method, 'reaches_mop') and method.reaches_mop
            )
        
        # Calculate window and transition coverage
        metrics.total_windows = len(static_data.windows.windows) if static_data.windows else 0
        # WindowTransitionGraph doesn't have 'edges' attribute directly, use 'transitions'
        metrics.total_transitions = (
            len(static_data.wtg.transitions) 
            if static_data.wtg and hasattr(static_data.wtg, 'transitions') 
            else 0
        )
        
        # Calculate security method coverage
        security_methods = {}
        for cls in static_data.classes.classes.values():
            # methods is a Set, not a Dict with items()
            for method in cls.methods:
                if hasattr(method, 'reaches_mop') and method.reaches_mop:
                    method_id = f"{cls.name}.{method.name}" if hasattr(method, 'name') else f"{cls.name}.unknown"
                    security_methods[method_id] = method
        
        metrics.total_security_methods = len(security_methods)
        
        # If we have logcat data, calculate traversed windows and transitions
        if self.logcat_data:
            # Identify visited windows and traversed transitions
            # Note: This would require a mapping between runtime activities and static windows
            # Simplified implementation for now:
            visited_windows = set()
            traversed_transitions = set()
            
            # Count visited security methods
            covered_security_methods = []
            for method_id, method in security_methods.items():
                class_name, method_name = method_id.rsplit('.', 1)
                # Check if this method was called in runtime
                if method_id in metrics.covered_methods:
                    covered_security_methods.append(method_id)
            
            metrics.covered_security_methods = covered_security_methods
            metrics.called_security_methods = len(covered_security_methods)
            
            # Calculate security method coverage
            if metrics.total_security_methods > 0:
                metrics.security_method_coverage = (
                    metrics.called_security_methods / metrics.total_security_methods
                ) * 100
            
            # For now, we'll use placeholders for window and transition coverage
            metrics.visited_windows = 0
            metrics.traversed_transitions = 0
            metrics.window_coverage = 0.0
            metrics.transition_coverage = 0.0
            
        return metrics
    
    def _calculate_monitored_operations_metrics(self) -> MonitoredOperationsMetrics:
        """
        Calculate monitored operations metrics from available data.
        
        This method analyzes both static and runtime data to calculate metrics about
        operations being monitored by specifications, including their violations
        and patterns of behavior.
        
        Returns:
            MonitoredOperationsMetrics with monitored operations information
        """
        metrics = MonitoredOperationsMetrics()
        
        # If no data available, return empty metrics
        if not self.static_data and not self.logcat_data:
            return metrics
            
        # Calculate metrics from static data
        if self.static_data:
            # Count MOP specifications
            mop_specs = set()
            spec_operation_map = {}
            monitored_operations_count = 0
            
            for cls in self.static_data.classes.classes.values():
                # methods is a Set, not a Dict with values()
                for method in cls.methods:
                    if (hasattr(method, 'reaches_mop') and method.reaches_mop and 
                        hasattr(method, 'mop_specs') and method.mop_specs):
                        # Add to specifications set
                        mop_specs.update(method.mop_specs)
                        
                        # Track monitored operations
                        monitored_operations_count += 1
                        
                        # Map specifications to operations
                        method_id = f"{cls.name}.{method.name}" if hasattr(method, 'name') else f"{cls.name}.unknown"
                        for spec in method.mop_specs:
                            if spec not in spec_operation_map:
                                spec_operation_map[spec] = []
                            spec_operation_map[spec].append(method_id)
            
            metrics.mop_specifications = len(mop_specs)
            metrics.spec_operation_map = spec_operation_map
            metrics.monitored_operations_count = monitored_operations_count
        
        # Calculate metrics from logcat data
        if self.logcat_data:
            # Count triggered specifications
            triggered_specs = set()
            spec_trigger_count = {}
            spec_categories = {}
            monitored_operations_triggered = 0
            operation_sequence_patterns = {}
            common_violation_contexts = {}
            
            for error in self.logcat_data.errors:
                # RvErrorLog has 'spec' attribute, not 'mop_spec'
                if hasattr(error, 'spec') and error.spec:
                    # Add to triggered specifications
                    spec = error.spec
                    triggered_specs.add(spec)
                    
                    # Count triggers per specification
                    spec_trigger_count[spec] = spec_trigger_count.get(spec, 0) + 1
                    
                    # Count monitored operations triggered
                    monitored_operations_triggered += 1
                    
                    # Count specification categories
                    if hasattr(error, 'error_type') and error.error_type:
                        category = error.error_type
                        spec_categories[category] = spec_categories.get(category, 0) + 1
                    
                    # Track violation context if available
                    if hasattr(error, 'context') and error.context:
                        context = error.context
                        common_violation_contexts[context] = common_violation_contexts.get(context, 0) + 1
                        
                    # Track operation sequence patterns if available
                    if hasattr(error, 'operation_sequence') and error.operation_sequence:
                        sequence = error.operation_sequence
                        operation_sequence_patterns[sequence] = operation_sequence_patterns.get(sequence, 0) + 1
            
            metrics.triggered_specifications = triggered_specs
            metrics.mop_triggers = len(self.logcat_data.errors)
            metrics.spec_trigger_count = spec_trigger_count
            metrics.spec_categories = spec_categories
            metrics.monitored_operations_triggered = monitored_operations_triggered
            metrics.operation_sequence_patterns = operation_sequence_patterns
            metrics.common_violation_contexts = common_violation_contexts
            
        return metrics