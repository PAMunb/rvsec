# tests/util/error/test_package_structure.py - Updated to fix assertion
"""
Tests for the package structure of the error handling system.
Ensures that all required modules and classes are available.
"""

import os

# Import the handler_registry module to get its path
from rv_android_core.util.error import handler_registry


def test_error_package_exports():
    """Test that the error package exports expected components."""
    # Import the components from the package
    from rv_android_core.util.error import HandlerRegistry
    from rv_android_core.util.error import RecoveryStrategies
    from rv_android_core.util.error import handle_errors
    from rv_android_core.util.error import retry

    # Verify that all expected components are exported
    assert HandlerRegistry is not None
    assert RecoveryStrategies is not None
    assert handle_errors is not None
    assert retry is not None


def test_error_package_structure():
    """Test that the error package has the expected structure."""
    # Get the path to the error package
    error_path = os.path.dirname(os.path.abspath(handler_registry.__file__))

    # Check that expected modules exist
    assert os.path.exists(os.path.join(error_path, "handler_registry.py"))
    assert os.path.exists(os.path.join(error_path, "recovery_strategies.py"))
    assert os.path.exists(os.path.join(error_path, "context_managers.py"))
    assert os.path.exists(os.path.join(error_path, "decorators.py"))
    assert os.path.exists(os.path.join(error_path, "__init__.py"))
