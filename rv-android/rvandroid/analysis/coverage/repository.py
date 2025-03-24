# rvandroid/analysis/coverage/repository.py
"""
Repository for storing and analyzing coverage data.
Provides a unified interface for coverage operations.
"""
from typing import Dict

from rvandroid.domain.coverage import LogcatRepository
from rvandroid.domain.log import RvCoverageLog, RvErrorLog
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class CoverageRepository:
    """
    Wrapper for the LogcatRepository to provide cleaner API.
    Acts as a facade to simplify common coverage operations.

    ### Architectural Decisions:
    - Serves as a facade for the core LogcatRepository
    - Simplifies common coverage operations
    - Provides a cleaner, more focused API

    ### Role in the System:
    - Centralizes coverage data management
    - Provides consistent access to coverage metrics
    - Simplifies repository interactions for clients
    """

    def __init__(self):
        """Initialize the coverage repository."""
        self.logger = LoggingManager.get_instance().get_logger(
            'analysis.coverage.repository',
            {CONTEXT_COMPONENT: 'CoverageRepository'}
        )

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

    def register_error(self, error_log: RvErrorLog) -> None:
        """
        Register an error in the repository.

        Args:
            error_log: Error log entry
        """
        self.repository.register_rv_error(error_log)

    def get_metrics(self, restrict_to_static: bool = True) -> Dict[str, float]:
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
    def errors(self):
        """
        Access the errors list from the underlying repository.

        Returns:
            List of errors
        """
        return self.repository.errors
