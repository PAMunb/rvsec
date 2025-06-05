# rvandroid/analysis/coverage/repository.py
"""
Repository for storing and analyzing coverage data.
Provides a unified interface for coverage operations.
"""
from typing import Dict, List, Any

from rvandroid.analysis.base_analyzer import BaseRepository
from rvandroid.domain.coverage import LogcatRepository
from rvandroid.domain.log import RvCoverageLog, RvErrorLog


class CoverageRepository(BaseRepository):
    """
    Wrapper for the LogcatRepository to provide cleaner API.
    Acts as a facade to simplify common coverage operations.

    ### Architectural Decisions:
    - Serves as a facade for the core LogcatRepository
    - Simplifies common coverage operations
    - Provides a cleaner, more focused API
    - Extends BaseRepository for consistent interface

    ### Role in the System:
    - Centralizes coverage data management
    - Provides consistent access to coverage metrics
    - Simplifies repository interactions for clients
    """

    def __init__(self):
        """Initialize the coverage repository."""
        super().__init__(repository_name="coverage")

        # Core repository - the source of truth
        self.repository = LogcatRepository()

    @property
    def classes(self):
        """
        Access the classes dictionary from the underlying repository.

        Returns:
            Dictionary of classes
        """
        return self.repository.classes

    def register_method_call(self, coverage_log: RvCoverageLog) -> None:
        """
        Register a method call in the repository.

        Args:
            coverage_log: Coverage log entry
        """
        self.repository.register_method_call(coverage_log)
        self.log_storage_summary("method call", 1)

    def register_error(self, error_log: RvErrorLog) -> None:
        """
        Register an error in the repository.

        Args:
            error_log: Error log entry
        """
        self.repository.register_rv_error(error_log)
        self.log_storage_summary("error", 1)

    def get_metrics(self, restrict_to_static: bool = True) -> Dict[str, Any]:
        """
        Get coverage metrics.

        Args:
            restrict_to_static: Whether to restrict to static analysis methods

        Returns:
            Dictionary of coverage metrics
        """
        metrics = self.repository.calculate_metrics(restrict_to_static)
        return metrics.to_dict()

    def get_error_count(self) -> int:
        """
        Get the count of unique errors.

        Returns:
            Number of unique errors
        """
        return len(self.repository.unique_errors)

    def get_method_call_count(self) -> int:
        """
        Get the count of method calls.

        Returns:
            Number of method calls
        """
        return self.repository.calculate_metrics().called_methods

    def get_underlying_repository(self) -> LogcatRepository:
        """
        Get the underlying LogcatRepository.

        Returns:
            LogcatRepository instance
        """
        return self.repository

    def calculate_metrics(self, restrict_to_static: bool = True):
        """
        Calculate metrics directly from the underlying repository.

        Args:
            restrict_to_static: Whether to restrict to static analysis methods

        Returns:
            Metrics object (not a dictionary)
        """
        return self.repository.calculate_metrics(restrict_to_static)

    @property
    def errors(self) -> List:
        """
        Access the errors list from the underlying repository.

        Returns:
            List of errors
        """
        return self.repository.errors

    def get_method_calls(self) -> List[Dict[str, Any]]:
        """
        Get all method calls as a list of dictionaries for export/reporting.
        Delegates to the underlying LogcatRepository.
        
        Returns:
            List of method call dictionaries with timing information
        """
        return self.repository.get_method_calls()

    def get_errors(self) -> List[Dict[str, Any]]:
        """
        Get all monitored operations errors as a list of dictionaries for export/reporting.
        Delegates to the underlying LogcatRepository.
        
        Returns:
            List of error dictionaries with details
        """
        return self.repository.get_errors()

    def get_static_methods(self) -> List[str]:
        """
        Get all method signatures from static analysis.
        Delegates to the underlying LogcatRepository.
        
        Returns:
            List of method signatures
        """
        return self.repository.get_static_methods()

    def get_static_activities(self) -> List[str]:
        """
        Get all activity class names from static analysis.
        Delegates to the underlying LogcatRepository.
        
        Returns:
            List of activity class names
        """
        return self.repository.get_static_activities()

    def get_mop_methods(self) -> List[str]:
        """
        Get all MOP-reachable method signatures from static analysis.
        Delegates to the underlying LogcatRepository.
        
        Returns:
            List of MOP-reachable method signatures
        """
        return self.repository.get_mop_methods()
