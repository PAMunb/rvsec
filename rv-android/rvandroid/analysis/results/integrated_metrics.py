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
class SecurityMetrics:
    """
    Security-specific metrics for application analysis.
    
    Captures detailed metrics about security-relevant aspects of the application,
    including vulnerabilities, MOP specifications, and potential issues.
    """
    mop_specifications: int = 0
    mop_triggers: int = 0
    triggered_specifications: Set[str] = field(default_factory=set)
    potential_vulnerabilities: int = 0
    detected_vulnerabilities: int = 0
    vulnerability_categories: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        # Convert sets to lists for JSON serialization
        if 'triggered_specifications' in data:
            data['triggered_specifications'] = list(data['triggered_specifications'])
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SecurityMetrics':
        """Create from dictionary."""
        # Handle special fields
        if 'triggered_specifications' in data and isinstance(data['triggered_specifications'], list):
            triggered_specifications = set(data['triggered_specifications'])
        else:
            triggered_specifications = set()
            
        if 'vulnerability_categories' in data and isinstance(data['vulnerability_categories'], dict):
            vulnerability_categories = data['vulnerability_categories']
        else:
            vulnerability_categories = {}
            
        return cls(
            mop_specifications=data.get('mop_specifications', 0),
            mop_triggers=data.get('mop_triggers', 0),
            triggered_specifications=triggered_specifications,
            potential_vulnerabilities=data.get('potential_vulnerabilities', 0),
            detected_vulnerabilities=data.get('detected_vulnerabilities', 0),
            vulnerability_categories=vulnerability_categories
        )


@dataclass
class IntegratedAnalysisResult:
    """
    Comprehensive integrated analysis result.
    
    Combines static analysis metrics, runtime coverage, and security metrics
    into a unified analysis result for a complete view of the application.
    """
    app_id: str
    static_metrics: StaticAnalysisMetrics
    coverage: IntegratedCoverageMetrics
    security: SecurityMetrics
    performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    errors: ErrorMetrics = field(default_factory=ErrorMetrics)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'app_id': self.app_id,
            'timestamp': self.timestamp,
            'static_metrics': self.static_metrics.to_dict(),
            'coverage': self.coverage.to_dict(),
            'security': self.security.to_dict(),
            'performance': self.performance.to_dict(),
            'errors': self.errors.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IntegratedAnalysisResult':
        """Create from dictionary."""
        # Convert component metrics
        static_metrics = StaticAnalysisMetrics.from_dict(data.get('static_metrics', {}))
        coverage = IntegratedCoverageMetrics.from_dict(data.get('coverage', {}))
        security = SecurityMetrics.from_dict(data.get('security', {}))
        performance = PerformanceMetrics.from_dict(data.get('performance', {}))
        errors = ErrorMetrics.from_dict(data.get('errors', {}))
        
        # Create instance
        return cls(
            app_id=data.get('app_id', 'unknown'),
            static_metrics=static_metrics,
            coverage=coverage,
            security=security,
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
        
        Returns:
            IntegratedAnalysisResult with comprehensive metrics
        """
        self.logger.info(f"Calculating integrated metrics for {self.app_id}")
        self.logger.info(f"Static data available: {bool(self.static_data)}")
        self.logger.info(f"Logcat data available: {bool(self.logcat_data)}")
        
        # Initialize metrics
        static_metrics = self._calculate_static_metrics()
        coverage_metrics = self._calculate_coverage_metrics()
        security_metrics = self._calculate_security_metrics()
        
        # Create result
        result = IntegratedAnalysisResult(
            app_id=self.app_id,
            static_metrics=static_metrics,
            coverage=coverage_metrics,
            security=security_metrics
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
    
    def _calculate_security_metrics(self) -> SecurityMetrics:
        """
        Calculate security metrics from available data.
        
        Returns:
            SecurityMetrics with security-specific information
        """
        metrics = SecurityMetrics()
        
        # If no data available, return empty metrics
        if not self.static_data and not self.logcat_data:
            return metrics
            
        # Calculate metrics from static data
        if self.static_data:
            # Count MOP specifications
            mop_specs = set()
            for cls in self.static_data.classes.classes.values():
                # methods is a Set, not a Dict with values()
                for method in cls.methods:
                    if (hasattr(method, 'reaches_mop') and method.reaches_mop and 
                        hasattr(method, 'mop_specs') and method.mop_specs):
                        mop_specs.update(method.mop_specs)
            
            metrics.mop_specifications = len(mop_specs)
            metrics.potential_vulnerabilities = len(mop_specs)  # Assuming each spec represents a potential issue
        
        # Calculate metrics from logcat data
        if self.logcat_data:
            # Count triggered specifications
            triggered_specs = set()
            for error in self.logcat_data.errors:
                # RvErrorLog has 'spec' attribute, not 'mop_spec'
                if hasattr(error, 'spec') and error.spec:
                    triggered_specs.add(error.spec)
            
            metrics.triggered_specifications = triggered_specs
            metrics.mop_triggers = len(self.logcat_data.errors)
            metrics.detected_vulnerabilities = len(triggered_specs)
            
            # Count vulnerability categories
            vulnerability_categories = {}
            for error in self.logcat_data.errors:
                if hasattr(error, 'error_type') and error.error_type:
                    category = error.error_type
                    vulnerability_categories[category] = vulnerability_categories.get(category, 0) + 1
            
            metrics.vulnerability_categories = vulnerability_categories
            
        return metrics