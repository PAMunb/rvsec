# tests/model/test_framework.py
from typing import Any, Dict, Type


class ModelTestBase:
    """
    Base class for model unit tests.

    This class provides common functionality for testing model classes, including:
    - Helper methods for creating test instances
    - Common assertions for model validation
    - Utility methods for test data generation
    """

    @staticmethod
    def assert_dict_contains_subset(subset: Dict[str, Any], full_dict: Dict[str, Any]) -> None:
        """
        Assert that a dictionary contains all key-value pairs from a subset dictionary.

        Args:
            subset: Dictionary containing expected key-value pairs
            full_dict: Dictionary to check against
        """
        for key, value in subset.items():
            assert key in full_dict, f"Key '{key}' not found in dictionary"
            assert full_dict[key] == value, f"Value for key '{key}' does not match"

    @staticmethod
    def create_mock_data(cls: Type, **kwargs) -> Any:
        """
        Create and return a mock instance of the given class.

        Args:
            cls: The class to instantiate
            **kwargs: Arguments to pass to the class constructor

        Returns:
            An instance of cls initialized with kwargs
        """
        return cls(**kwargs)
