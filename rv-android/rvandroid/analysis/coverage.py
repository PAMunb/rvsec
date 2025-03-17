import copy

from rvandroid.constants import *
from rvandroid.model.log import RvCoverageLog
from typing import Dict, Any

from rvandroid.constants import *
from rvandroid.model.coverage import CoverageRepository, process_coverage_data
from rvandroid.model.log import RvCoverageLog


def process_coverage(called_methods: Dict[str, Dict[str, Dict[str, RvCoverageLog]]],
                     all_methods: Dict) -> Dict[str, Any]:
    """
    Process coverage data to calculate coverage metrics.
    This function is a facade that delegates to the new coverage model.

    Args:
        called_methods: Dictionary of called methods organized by class
        all_methods: Dictionary of all methods from static analysis

    Returns:
        Dictionary with coverage results
    """
    return process_coverage_data(called_methods, all_methods)


def calculate_coverage(total: int, called: int) -> float:
    """
    Calculate coverage percentage.

    Args:
        total: Total number of items
        called: Number of called/covered items

    Returns:
        Coverage percentage (0-100)
    """
    if total <= 0:
        return 0.0
    return (called * 100) / total
