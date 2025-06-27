# rvandroid/analysis/results/base_result.py
"""
Base result classes for standardized analysis results.

This module provides a set of base classes for representing analysis results
in a consistent way, making it easier to process, aggregate, and visualize
results from different analyzers.
"""

import json
import os
from abc import abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, TypeVar, Generic, Set


class ResultType(Enum):
    """Enumeration of possible result types."""
    COVERAGE = "coverage"
    VISUAL = "visual"
    PERFORMANCE = "performance"
    ERROR = "error"
    CUSTOM = "custom"


@dataclass
class BaseResult:
    """
    Base class for all analysis results.
    
    Provides common attributes and serialization methods.
    """
    # Basic metadata
    timestamp: datetime = field(default_factory=datetime.now)
    result_type: ResultType = ResultType.CUSTOM
    analyzer_name: str = "unnamed"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = asdict(self)
        # Convert timestamp to string
        data['timestamp'] = data['timestamp'].isoformat()
        # Convert enums to string values
        data['result_type'] = data['result_type'].value

        return data

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def save_to_file(self, file_path: str) -> None:
        """
        Save result to JSON file.
        
        Args:
            file_path: Path to save the result
        """
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseResult':
        """
        Create instance from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            Instance of this class
        """
        # Convert string timestamp to datetime
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])

        # Convert string result_type to enum
        if 'result_type' in data and isinstance(data['result_type'], str):
            data['result_type'] = ResultType(data['result_type'])

        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> 'BaseResult':
        """
        Create instance from JSON string.
        
        Args:
            json_str: JSON string representation
            
        Returns:
            Instance of this class
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def load_from_file(cls, file_path: str) -> 'BaseResult':
        """
        Load result from JSON file.
        
        Args:
            file_path: Path to load the result from
            
        Returns:
            Instance of this class
        """
        with open(file_path, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)


@dataclass
class CoverageResult(BaseResult):
    """
    Result for coverage analysis.
    
    Contains detailed coverage metrics for code and activities.
    """
    result_type: ResultType = ResultType.COVERAGE

    # Coverage metrics
    method_coverage: float = 0.0
    activity_coverage: float = 0.0
    mop_method_coverage: float = 0.0

    # Detailed counts
    total_methods: int = 0
    called_methods: int = 0
    total_activities: int = 0
    visited_activities: int = 0
    total_mop_methods: int = 0
    called_mop_methods: int = 0

    # Lists of covered elements
    covered_methods: List[str] = field(default_factory=list)
    covered_activities: List[str] = field(default_factory=list)
    covered_mop_methods: List[str] = field(default_factory=list)


@dataclass
class ErrorResult(BaseResult):
    """
    Result for error analysis.
    
    Contains error counts and detailed error information.
    """
    result_type: ResultType = ResultType.ERROR

    # Error metrics
    total_errors: int = 0
    unique_errors: int = 0

    # Detailed error information
    error_types: Dict[str, int] = field(default_factory=dict)
    error_locations: Dict[str, int] = field(default_factory=dict)

    # List of error details
    errors: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class VisualResult(BaseResult):
    """
    Result for visual analysis.
    
    Contains metrics and findings from visual analysis.
    """
    result_type: ResultType = ResultType.VISUAL

    # Visual metrics
    total_screens: int = 0
    total_visual_elements: int = 0
    error_indicators: int = 0

    # Screen details
    screen_details: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Paths to screenshots
    screenshot_paths: List[str] = field(default_factory=list)


@dataclass
class PerformanceResult(BaseResult):
    """
    Result for performance analysis.
    
    Contains performance metrics like execution time, memory usage, etc.
    """
    result_type: ResultType = ResultType.PERFORMANCE

    # Performance metrics
    execution_time: float = 0.0  # in seconds
    memory_usage: float = 0.0  # in MB
    cpu_usage: float = 0.0  # percentage

    # Timeline data for visualization
    timeline: List[Dict[str, Any]] = field(default_factory=list)


T = TypeVar('T', bound=BaseResult)


class ResultAggregator(Generic[T]):
    """
    Generic aggregator for analysis results.
    
    Collects and aggregates results of the same type.
    """

    def __init__(self, result_type: type[T]):
        """
        Initialize the aggregator.
        
        Args:
            result_type: Type of results to aggregate
        """
        self.result_type = result_type
        self.results: List[T] = []

    def add_result(self, result: T) -> None:
        """
        Add a result to the aggregator.
        
        Args:
            result: Result to add
        """
        if not isinstance(result, self.result_type):
            raise TypeError(f"Expected result of type {self.result_type.__name__}, got {type(result).__name__}")

        self.results.append(result)

    def get_results(self) -> List[T]:
        """
        Get all collected results.
        
        Returns:
            List of results
        """
        return self.results

    def clear(self) -> None:
        """Clear all collected results."""
        self.results.clear()

    @abstractmethod
    def aggregate(self) -> T:
        """
        Aggregate results into a single result.
        
        Returns:
            Aggregated result
        """
        pass


class CoverageResultAggregator(ResultAggregator[CoverageResult]):
    """Aggregator for coverage results."""

    def __init__(self):
        """Initialize the coverage result aggregator."""
        super().__init__(CoverageResult)

    def aggregate(self) -> CoverageResult:
        """
        Aggregate coverage results.
        
        Returns:
            Aggregated coverage result
        """
        if not self.results:
            return CoverageResult()

        # Initialize result with default values
        aggregated = CoverageResult(
            analyzer_name="aggregated",
            timestamp=datetime.now()
        )

        # Collect all covered elements
        all_covered_methods: Set[str] = set()
        all_covered_activities: Set[str] = set()
        all_covered_mop_methods: Set[str] = set()

        # Sum up metrics
        total_methods = 0
        total_activities = 0
        total_mop_methods = 0

        for result in self.results:
            # Update covered elements
            all_covered_methods.update(result.covered_methods)
            all_covered_activities.update(result.covered_activities)
            all_covered_mop_methods.update(result.covered_mop_methods)

            # Update totals
            total_methods = max(total_methods, result.total_methods)
            total_activities = max(total_activities, result.total_activities)
            total_mop_methods = max(total_mop_methods, result.total_mop_methods)

        # Update aggregated result
        aggregated.total_methods = total_methods
        aggregated.called_methods = len(all_covered_methods)
        aggregated.total_activities = total_activities
        aggregated.visited_activities = len(all_covered_activities)
        aggregated.total_mop_methods = total_mop_methods
        aggregated.called_mop_methods = len(all_covered_mop_methods)

        # Calculate coverage percentages
        if total_methods > 0:
            aggregated.method_coverage = 100 * aggregated.called_methods / total_methods
        if total_activities > 0:
            aggregated.activity_coverage = 100 * aggregated.visited_activities / total_activities
        if total_mop_methods > 0:
            aggregated.mop_method_coverage = 100 * aggregated.called_mop_methods / total_mop_methods

        # Convert sets to sorted lists
        aggregated.covered_methods = sorted(list(all_covered_methods))
        aggregated.covered_activities = sorted(list(all_covered_activities))
        aggregated.covered_mop_methods = sorted(list(all_covered_mop_methods))

        return aggregated


class ErrorResultAggregator(ResultAggregator[ErrorResult]):
    """Aggregator for error results."""

    def __init__(self):
        """Initialize the error result aggregator."""
        super().__init__(ErrorResult)

    def aggregate(self) -> ErrorResult:
        """
        Aggregate error results.
        
        Returns:
            Aggregated error result
        """
        if not self.results:
            return ErrorResult()

        # Initialize result with default values
        aggregated = ErrorResult(
            analyzer_name="aggregated",
            timestamp=datetime.now()
        )

        # Collect unique errors
        all_errors: List[Dict[str, Any]] = []
        unique_error_msgs: Set[str] = set()
        error_types: Dict[str, int] = {}
        error_locations: Dict[str, int] = {}

        for result in self.results:
            for error in result.errors:
                # Extract error message and add to unique set
                error_msg = error.get('message', '')
                unique_error_msgs.add(error_msg)

                # Add to all errors list
                all_errors.append(error)

                # Update error type counts
                error_type = error.get('type', 'unknown')
                error_types[error_type] = error_types.get(error_type, 0) + 1

                # Update error location counts
                error_loc = error.get('location', 'unknown')
                error_locations[error_loc] = error_locations.get(error_loc, 0) + 1

        # Update aggregated result
        aggregated.total_errors = len(all_errors)
        aggregated.unique_errors = len(unique_error_msgs)
        aggregated.error_types = error_types
        aggregated.error_locations = error_locations
        aggregated.errors = all_errors

        return aggregated
