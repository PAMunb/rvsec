# rvandroid/analysis/results/result_manager.py
"""
Result manager for collecting, storing, and retrieving analysis results.

This module provides a central manager for handling analysis results from
different analyzers, supporting result storage, aggregation, and export.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Type, TypeVar, Generic, Set, Union

from rvandroid.analysis.results.base_result import (
    BaseResult, CoverageResult, ErrorResult, VisualResult, PerformanceResult,
    ResultAggregator, CoverageResultAggregator, ErrorResultAggregator
)
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


T = TypeVar('T', bound=BaseResult)


class ResultManager:
    """
    Central manager for experiment result handling.

    ### Architectural Decisions:
    - Centralizes result collection and storage
    - Supports multiple result types and formats
    - Provides a unified interface for result handling
    - Enables result aggregation across multiple runs

    ### Role in the System:
    - Collects results from different analyzers
    - Handles result storage and retrieval
    - Supports result aggregation and comparison
    - Enables export to various formats
    """

    def __init__(self, results_dir: str = "results"):
        """
        Initialize the result manager.

        Args:
            results_dir: Directory for storing results
        """
        self.logger = LoggingManager.get_instance().get_logger(
            'analysis.results.manager',
            {CONTEXT_COMPONENT: 'ResultManager'}
        )

        # Set results directory
        self.results_dir = results_dir
        os.makedirs(results_dir, exist_ok=True)

        # Register known result types
        self.result_types: Dict[str, Type[BaseResult]] = {
            "coverage": CoverageResult,
            "error": ErrorResult,
            "visual": VisualResult,
            "performance": PerformanceResult
        }

        # Initialize result storage
        self.results: Dict[str, Dict[str, List[BaseResult]]] = {}
        self.aggregators: Dict[str, ResultAggregator] = {
            "coverage": CoverageResultAggregator(),
            "error": ErrorResultAggregator()
        }

        # Try to load existing results
        self._load_existing_results()

    def add_result(self, result: BaseResult, app_id: str = "default") -> None:
        """
        Add a result to the manager.

        Args:
            result: Result to add
            app_id: Application identifier
        """
        # Get result type as string
        result_type = result.result_type.value

        # Initialize storage if needed
        if app_id not in self.results:
            self.results[app_id] = {}
        if result_type not in self.results[app_id]:
            self.results[app_id][result_type] = []

        # Store result
        self.results[app_id][result_type].append(result)

        # Add to aggregator if available
        if result_type in self.aggregators:
            try:
                self.aggregators[result_type].add_result(result)
            except TypeError:
                self.logger.warning(f"Failed to add result to aggregator for type {result_type}")

        # Save result to file
        self._save_result(result, app_id, result_type)

        self.logger.debug(f"Added {result_type} result for app {app_id}")

    def get_results(self, app_id: Optional[str] = None, 
                    result_type: Optional[str] = None) -> List[BaseResult]:
        """
        Get results from the manager.

        Args:
            app_id: Application identifier (None for all)
            result_type: Type of results to get (None for all)

        Returns:
            List of matching results
        """
        results = []

        # Determine which apps to include
        app_ids = [app_id] if app_id else list(self.results.keys())

        for app in app_ids:
            if app not in self.results:
                continue

            # Determine which result types to include
            result_types = [result_type] if result_type else list(self.results[app].keys())

            for rt in result_types:
                if rt in self.results[app]:
                    results.extend(self.results[app][rt])

        return results

    def get_aggregated_result(self, result_type: str) -> Optional[BaseResult]:
        """
        Get aggregated result for a type.

        Args:
            result_type: Type of result to aggregate

        Returns:
            Aggregated result or None if not available
        """
        if result_type not in self.aggregators:
            self.logger.warning(f"No aggregator available for type {result_type}")
            return None

        return self.aggregators[result_type].aggregate()

    def export_results(self, export_format: str = "json", 
                       output_file: Optional[str] = None) -> str:
        """
        Export all results to a file.

        Args:
            export_format: Format to export (json, csv)
            output_file: Output file path (None for default)

        Returns:
            Path to the exported file
        """
        if export_format != "json":
            self.logger.warning(f"Unsupported export format: {export_format}, using json")
            export_format = "json"

        # Generate default output file if not provided
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(self.results_dir, f"results_export_{timestamp}.json")

        # Prepare data for export
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "apps": {},
            "aggregated": {}
        }

        # Add app results
        for app_id, app_results in self.results.items():
            export_data["apps"][app_id] = {}
            for result_type, results in app_results.items():
                export_data["apps"][app_id][result_type] = [r.to_dict() for r in results]

        # Add aggregated results
        for result_type, aggregator in self.aggregators.items():
            aggregated = aggregator.aggregate()
            export_data["aggregated"][result_type] = aggregated.to_dict()

        # Export to file
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)

        self.logger.info(f"Exported results to {output_file}")
        return output_file

    def clear_results(self, app_id: Optional[str] = None, 
                      result_type: Optional[str] = None) -> None:
        """
        Clear results from the manager.

        Args:
            app_id: Application identifier (None for all)
            result_type: Type of results to clear (None for all)
        """
        # Determine which apps to clear
        app_ids = [app_id] if app_id else list(self.results.keys())

        for app in app_ids:
            if app not in self.results:
                continue

            # Determine which result types to clear
            result_types = [result_type] if result_type else list(self.results[app].keys())

            for rt in result_types:
                if rt in self.results[app]:
                    self.results[app][rt] = []

        # Reset aggregators if needed
        if result_type is None:
            for agg in self.aggregators.values():
                agg.clear()
        elif result_type in self.aggregators:
            self.aggregators[result_type].clear()

        self.logger.info(f"Cleared results for app={app_id}, type={result_type}")

    def _save_result(self, result: BaseResult, app_id: str, result_type: str) -> None:
        """
        Save a result to a file.

        Args:
            result: Result to save
            app_id: Application identifier
            result_type: Type of result
        """
        # Create app directory if needed
        app_dir = os.path.join(self.results_dir, app_id)
        os.makedirs(app_dir, exist_ok=True)

        # Generate filename
        timestamp = result.timestamp.strftime("%Y%m%d_%H%M%S")
        analyzer = result.analyzer_name
        filename = f"{result_type}_{analyzer}_{timestamp}.json"
        file_path = os.path.join(app_dir, filename)

        # Save result
        result.save_to_file(file_path)

    def _load_existing_results(self) -> None:
        """
        Load existing results from the results directory.
        """
        if not os.path.exists(self.results_dir):
            return

        # Scan for app directories
        for app_id in os.listdir(self.results_dir):
            app_dir = os.path.join(self.results_dir, app_id)
            if not os.path.isdir(app_dir):
                continue

            # Scan for result files
            for filename in os.listdir(app_dir):
                if not filename.endswith(".json"):
                    continue

                file_path = os.path.join(app_dir, filename)
                try:
                    # Determine result type from filename
                    parts = filename.split("_")
                    if len(parts) < 2:
                        continue

                    result_type = parts[0]
                    if result_type not in self.result_types:
                        continue

                    # Load the result
                    try:
                        result_class = self.result_types[result_type]
                        
                        # Try to load the file
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                            
                        # Filter out unexpected keyword arguments
                        if result_type == "coverage" and "tasks" in data:
                            del data["tasks"]
                        
                        if result_type == "error" and "errors_by_app" in data:
                            del data["errors_by_app"]
                            
                        # Create the object with filtered data
                        result = result_class.from_dict(data)

                        # Add to storage
                        if app_id not in self.results:
                            self.results[app_id] = {}
                        if result_type not in self.results[app_id]:
                            self.results[app_id][result_type] = []

                        self.results[app_id][result_type].append(result)

                        # Add to aggregator
                        if result_type in self.aggregators:
                            try:
                                self.aggregators[result_type].add_result(result)
                            except TypeError:
                                self.logger.warning(f"Failed to add result to aggregator for type {result_type}")
                    except json.JSONDecodeError:
                        self.logger.warning(f"Failed to parse JSON from {file_path}")
                    except KeyError as ke:
                        self.logger.warning(f"Missing key in result data: {ke}")

                except Exception as e:
                    self.logger.warning(f"Failed to load result from {file_path}: {e}")

        # Log summary
        app_count = len(self.results)
        result_count = sum(
            len(results)
            for app_results in self.results.values()
            for results in app_results.values()
        )
        self.logger.info(f"Loaded {result_count} existing results for {app_count} apps")


def create_coverage_result_from_metrics(
    metrics: Dict[str, Any], 
    analyzer_name: str = "coverage_analyzer"
) -> CoverageResult:
    """
    Create a CoverageResult from metrics dictionary.

    Args:
        metrics: Metrics dictionary
        analyzer_name: Name of the analyzer

    Returns:
        CoverageResult instance
    """
    result = CoverageResult(
        analyzer_name=analyzer_name,
        timestamp=datetime.now()
    )
    
    # Set coverage metrics
    result.method_coverage = metrics.get("method_coverage", 0.0)
    result.activity_coverage = metrics.get("activity_coverage", 0.0)
    result.mop_method_coverage = metrics.get("mop_method_coverage", 0.0)
    
    # Set detailed counts
    result.total_methods = metrics.get("total_methods", 0)
    result.called_methods = metrics.get("called_methods", 0)
    result.total_activities = metrics.get("total_activities", 0)
    result.visited_activities = metrics.get("visited_activities", 0)
    result.total_mop_methods = metrics.get("total_mop_methods", 0)
    result.called_mop_methods = metrics.get("called_mop_methods", 0)
    
    # Set covered elements if available
    if "covered_methods" in metrics:
        result.covered_methods = metrics["covered_methods"]
    if "covered_activities" in metrics:
        result.covered_activities = metrics["covered_activities"]
    if "covered_mop_methods" in metrics:
        result.covered_mop_methods = metrics["covered_mop_methods"]
    
    return result


def create_error_result_from_errors(
    errors: List[Dict[str, Any]], 
    analyzer_name: str = "error_analyzer"
) -> ErrorResult:
    """
    Create an ErrorResult from a list of errors.

    Args:
        errors: List of error dictionaries
        analyzer_name: Name of the analyzer

    Returns:
        ErrorResult instance
    """
    result = ErrorResult(
        analyzer_name=analyzer_name,
        timestamp=datetime.now()
    )
    
    # Set error list
    result.errors = errors
    
    # Calculate metrics
    result.total_errors = len(errors)
    
    # Extract unique error messages
    unique_messages = set()
    error_types = {}
    error_locations = {}
    
    for error in errors:
        # Get message for uniqueness calculation
        message = error.get("message", "")
        unique_messages.add(message)
        
        # Update error type counts
        error_type = error.get("type", "unknown")
        error_types[error_type] = error_types.get(error_type, 0) + 1
        
        # Update error location counts
        location = error.get("location", "unknown")
        error_locations[location] = error_locations.get(location, 0) + 1
    
    # Set metrics
    result.unique_errors = len(unique_messages)
    result.error_types = error_types
    result.error_locations = error_locations
    
    return result