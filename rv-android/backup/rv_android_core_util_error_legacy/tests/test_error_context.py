# tests/util/error/test_error_context.py
"""
Unit tests for the ErrorContext module.

This test suite covers the functionality of the ErrorContext class,
which provides fluent context building and auto-introspection capabilities
for enhanced error handling.
"""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

# Ensure the parent directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from rv_android_core.util.error.context import ErrorContext
from rv_android_core.util.error.error_handler import ErrorHandler


class TestErrorContext:
    """
    Comprehensive test suite for the ErrorContext class.
    
    ### Testing Strategy:
    - Validate fluent API functionality
    - Test auto-introspection capabilities
    - Verify context building accuracy
    - Ensure backward compatibility
    """

    def test_basic_context_creation(self):
        """
        Test basic ErrorContext creation and building.
        
        Validates:
        - Context can be created with initial data
        - Build method returns proper dictionary
        - Auto-introspection is enabled by default
        """
        context = ErrorContext(test_key="test_value")
        built_context = context.build()
        
        # Should include the initial data
        assert built_context["test_key"] == "test_value"
        
        # Should include auto-introspected data
        assert "caller_function" in built_context
        assert "caller_filename" in built_context
        assert "caller_line" in built_context

    def test_fluent_api_chaining(self):
        """
        Test fluent API method chaining.
        
        Validates:
        - Methods return self for chaining
        - All fluent methods work correctly
        - Final context includes all data
        """
        context = ErrorContext()\
            .with_component("TestComponent")\
            .with_phase("testing")\
            .with_data(task_id=123, app_name="TestApp")
        
        built_context = context.build()
        
        assert built_context["component"] == "TestComponent"
        assert built_context["phase"] == "testing"
        assert built_context["task_id"] == 123
        assert built_context["app_name"] == "TestApp"

    def test_disable_introspection(self):
        """
        Test disabling auto-introspection.
        
        Validates:
        - Introspection can be disabled
        - Manual context data is preserved
        - No caller information is added when disabled
        """
        context = ErrorContext(manual_data="test")\
            .disable_introspection()\
            .with_component("TestComponent")
        
        built_context = context.build()
        
        # Should have manual data
        assert built_context["manual_data"] == "test"
        assert built_context["component"] == "TestComponent"
        
        # Should not have auto-introspected data
        assert "caller_function" not in built_context
        assert "caller_filename" not in built_context

    def test_enable_introspection(self):
        """
        Test enabling introspection after disabling.
        
        Validates:
        - Introspection can be re-enabled
        - Caller information is captured when enabled
        """
        context = ErrorContext()\
            .disable_introspection()\
            .enable_introspection()\
            .with_component("TestComponent")
        
        built_context = context.build()
        
        # Should have introspected data since it was re-enabled
        assert "caller_function" in built_context
        assert built_context["component"] == "TestComponent"

    def test_to_dict_compatibility(self):
        """
        Test to_dict method for backward compatibility.
        
        Validates:
        - to_dict returns same as build()
        - Provides backward compatibility
        """
        # Disable introspection to avoid timing differences
        context = ErrorContext(test_data="value", auto_introspect=False)\
            .with_component("TestComponent")
        
        dict_result = context.to_dict()
        build_result = context.build()
        
        # Results should be identical
        assert dict_result == build_result
        assert dict_result["test_data"] == "value"
        assert dict_result["component"] == "TestComponent"

    def test_handle_method_integration(self):
        """
        Test handle method integration with ErrorHandler.
        
        Validates:
        - handle method calls ErrorHandler correctly
        - Context is properly passed
        - Error handling works end-to-end
        """
        # Create mock error handler
        mock_handler = MagicMock()
        mock_handler.handle_error.return_value = True
        
        # Create context and test error
        context = ErrorContext()\
            .with_component("TestComponent")\
            .with_phase("testing")
        
        test_error = ValueError("Test error")
        
        # Handle the error
        result = context.handle(test_error, mock_handler)
        
        # Verify ErrorHandler was called correctly
        assert result is True
        mock_handler.handle_error.assert_called_once()
        
        # Verify the call arguments
        call_args = mock_handler.handle_error.call_args
        assert call_args[0][0] == test_error  # First arg is the error
        context_arg = call_args[0][1]         # Second arg is the context
        assert context_arg["component"] == "TestComponent"
        assert context_arg["phase"] == "testing"

    def test_frame_offset_introspection(self):
        """
        Test frame offset handling in introspection.
        
        Validates:
        - Different frame offsets capture different callers
        - Introspection works correctly at various call depths
        """
        def nested_function():
            context = ErrorContext()
            return context.build(frame_offset=1)  # Should capture this function
        
        def calling_function():
            return nested_function()
        
        # Call through nested functions
        built_context = calling_function()
        
        # Should capture the nested_function as caller
        assert built_context["caller_function"] == "nested_function"

    def test_introspection_with_class_method(self):
        """
        Test introspection when called from class methods.
        
        Validates:
        - Class name is captured when called from instance methods
        - Component is auto-detected from class name
        """
        class TestClass:
            def test_method(self):
                context = ErrorContext()
                # Use frame_offset=1 to capture this method specifically
                return context.build(frame_offset=1)
        
        test_instance = TestClass()
        built_context = test_instance.test_method()
        
        # Should capture method information
        assert built_context["caller_function"] == "test_method"
        # Should capture class information when using frame_offset=1
        assert built_context["caller_class"] == "TestClass"
        # Component should be auto-detected from class name
        assert built_context["component"] == "TestClass"

    def test_introspection_failure_handling(self):
        """
        Test introspection failure handling.
        
        Validates:
        - Introspection failures don't break context building
        - Manual context data is preserved even if introspection fails
        """
        # Mock inspect.currentframe to raise an exception
        with patch('rv_android_core.util.error.context.inspect.currentframe', side_effect=Exception("Mock failure")):
            context = ErrorContext(manual_data="preserved")\
                .with_component("TestComponent")
            
            built_context = context.build()
            
            # Manual data should be preserved
            assert built_context["manual_data"] == "preserved"
            assert built_context["component"] == "TestComponent"
            
            # Introspected data should not be present
            assert "caller_function" not in built_context

    def test_string_representations(self):
        """
        Test string representations of ErrorContext.
        
        Validates:
        - __str__ provides readable representation
        - __repr__ provides detailed representation
        """
        context = ErrorContext()\
            .with_component("TestComponent")\
            .with_phase("testing")
        
        str_repr = str(context)
        repr_repr = repr(context)
        
        # String representation should be readable
        assert "TestComponent" in str_repr
        assert "testing" in str_repr
        assert "ErrorContext" in str_repr
        
        # Detailed representation should include more information
        assert "ErrorContext" in repr_repr

    def test_context_data_override(self):
        """
        Test context data override behavior.
        
        Validates:
        - Later data overrides earlier data
        - with_data can override previous values
        - Component and phase can be overridden
        """
        context = ErrorContext(test_key="original")\
            .with_component("FirstComponent")\
            .with_phase("first_phase")\
            .with_data(test_key="overridden")\
            .with_component("SecondComponent")
        
        built_context = context.build()
        
        # Later values should override earlier ones
        assert built_context["test_key"] == "overridden"
        assert built_context["component"] == "SecondComponent"
        assert built_context["phase"] == "first_phase"  # Not overridden

    def test_empty_context(self):
        """
        Test empty context behavior.
        
        Validates:
        - Empty context can be created
        - Auto-introspection still works
        - No manual data doesn't break functionality
        """
        context = ErrorContext()
        built_context = context.build()
        
        # Should have auto-introspected data
        assert "caller_function" in built_context
        
        # Should not have any manual data
        assert len([k for k in built_context.keys() if not k.startswith("caller")]) == 0


if __name__ == "__main__":
    pytest.main(["-v", "test_error_context.py"])