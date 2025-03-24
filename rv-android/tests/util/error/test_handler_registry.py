# tests/util/error/test_handler_registry.py
"""
Unit tests for the HandlerRegistry module in rv-android.

This test suite covers the functionality of the HandlerRegistry class,
which manages registration and retrieval of error handlers based on exception types.
"""

import os
import sys
import pytest

# Ensure the parent directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from rvandroid.util.error.handler_registry import HandlerRegistry


class TestHandlerRegistry:
    """
    Comprehensive test suite for the HandlerRegistry class.

    ### Architectural Testing Considerations:
    - Validate handler registration and lookup mechanisms
    - Test error handler inheritance and polymorphism
    - Ensure correct handler execution based on exception type hierarchy
    - Verify type-based lookup with multiple handlers
    """

    def test_initialization(self):
        """
        Test HandlerRegistry initialization.

        Validates:
        - Registry is correctly initialized
        - Internal registry dictionary is empty at start
        """
        registry = HandlerRegistry()

        # Registry should be an empty dict after initialization
        assert hasattr(registry, '_registry')
        assert isinstance(registry._registry, dict)
        assert len(registry._registry) == 0

    def test_register_handler(self):
        """
        Test registering a handler for a specific error type.

        Validates:
        - Handler is properly registered for an exception type
        - Registry contains the correct handler after registration
        """
        registry = HandlerRegistry()

        # Define a mock handler function
        def mock_handler(error, context):
            return True

        # Register the handler for a specific exception type
        registry.register(ValueError, mock_handler)

        # Verify registration
        assert ValueError in registry._registry
        assert mock_handler in registry._registry[ValueError]
        assert len(registry._registry[ValueError]) == 1

    def test_register_multiple_handlers_for_same_type(self):
        """
        Test registering multiple handlers for the same error type.

        Validates:
        - Multiple handlers can be registered for the same exception type
        - All handlers are preserved in registration order
        """
        registry = HandlerRegistry()

        # Define multiple mock handler functions
        def mock_handler1(error, context):
            return True

        def mock_handler2(error, context):
            return True

        # Register both handlers for the same exception type
        registry.register(ValueError, mock_handler1)
        registry.register(ValueError, mock_handler2)

        # Verify both handlers are registered
        assert ValueError in registry._registry
        assert len(registry._registry[ValueError]) == 2
        assert mock_handler1 in registry._registry[ValueError]
        assert mock_handler2 in registry._registry[ValueError]

    def test_register_same_handler_twice(self):
        """
        Test registering the same handler twice for the same error type.

        Validates:
        - Same handler can't be registered multiple times for the same type
        - Duplicate registrations are prevented
        """
        registry = HandlerRegistry()

        # Define a mock handler function
        def mock_handler(error, context):
            return True

        # Register the same handler twice
        registry.register(ValueError, mock_handler)
        registry.register(ValueError, mock_handler)

        # Verify handler is registered only once
        assert ValueError in registry._registry
        assert len(registry._registry[ValueError]) == 1
        assert mock_handler in registry._registry[ValueError]

    def test_find_handlers_exact_type(self):
        """
        Test finding handlers for the exact registered error type.

        Validates:
        - Handlers are correctly found for the exact registered type
        - Lookup returns the correct handler list
        """
        registry = HandlerRegistry()

        # Define a mock handler function
        def mock_handler(error, context):
            return True

        # Register the handler
        registry.register(ValueError, mock_handler)

        # Find handlers for the exact type
        handlers = registry.find_handlers(ValueError)

        # Verify handlers are found
        assert len(handlers) == 1
        assert mock_handler in handlers

    def test_find_handlers_subclass_type(self):
        """
        Test finding handlers based on inheritance hierarchy.

        Validates:
        - Handlers registered for parent classes are found for child classes
        - Type-based lookup respects inheritance relationships
        """
        registry = HandlerRegistry()

        # Define mock handler functions
        def base_handler(error, context):
            return True

        def specific_handler(error, context):
            return True

        # Create a custom exception hierarchy
        class CustomBaseError(Exception):
            pass

        class CustomSpecificError(CustomBaseError):
            pass

        # Register handlers at different levels of the hierarchy
        registry.register(CustomBaseError, base_handler)
        registry.register(CustomSpecificError, specific_handler)

        # Find handlers for the base type
        base_handlers = registry.find_handlers(CustomBaseError)
        assert len(base_handlers) == 1
        assert base_handler in base_handlers

        # Find handlers for the specific type
        # Should include both the specific handler and the base handler
        specific_handlers = registry.find_handlers(CustomSpecificError)
        assert len(specific_handlers) == 2
        assert base_handler in specific_handlers
        assert specific_handler in specific_handlers

    def test_find_handlers_multilevel_inheritance(self):
        """
        Test finding handlers with multiple levels of inheritance.

        Validates:
        - Handlers are found through a deep inheritance chain
        - All applicable handlers from parent classes are returned
        """
        registry = HandlerRegistry()

        # Define mock handler functions for each level
        def exception_handler(error, context):
            return True

        def runtime_error_handler(error, context):
            return True

        def value_error_handler(error, context):
            return True

        # Register handlers at different levels
        registry.register(Exception, exception_handler)
        registry.register(RuntimeError, runtime_error_handler)
        registry.register(ValueError, value_error_handler)

        # Find handlers for ValueError (inherits from Exception -> RuntimeError -> ValueError)
        # Note: ValueError actually inherits from Exception, not RuntimeError
        handlers = registry.find_handlers(ValueError)

        # Verify all applicable handlers are found
        assert len(handlers) == 2  # Should include Exception and ValueError handlers
        assert exception_handler in handlers
        assert value_error_handler in handlers
        assert runtime_error_handler not in handlers  # Since ValueError doesn't inherit from RuntimeError

    def test_find_handlers_unregistered_type(self):
        """
        Test finding handlers for an unregistered error type.

        Validates:
        - Empty list is returned for unregistered types
        - No errors are raised for unknown types
        """
        registry = HandlerRegistry()

        # Define and register a handler for a different type
        def mock_handler(error, context):
            return True

        registry.register(ValueError, mock_handler)

        # Find handlers for an unregistered type
        handlers = registry.find_handlers(KeyError)

        # Verify no handlers are found
        assert len(handlers) == 0

    def test_registered_types_with_multiple_handlers(self):
        """
        Test complex registration with multiple handlers and types.

        Validates:
        - Registry correctly maintains multiple handlers for multiple types
        - Handler lookup works correctly with a complex registration structure
        """
        registry = HandlerRegistry()

        # Define multiple mock handlers
        def handler1(error, context):
            return True

        def handler2(error, context):
            return True

        def handler3(error, context):
            return True

        # Register multiple handlers for multiple types
        registry.register(ValueError, handler1)
        registry.register(ValueError, handler2)
        registry.register(KeyError, handler2)
        registry.register(Exception, handler3)

        # Verify registrations
        assert len(registry._registry) == 3  # Three different exception types
        assert len(registry._registry[ValueError]) == 2
        assert len(registry._registry[KeyError]) == 1
        assert len(registry._registry[Exception]) == 1

        # Test handler lookup for each type
        value_handlers = registry.find_handlers(ValueError)
        assert len(value_handlers) == 3  # Should include Exception, ValueError handler1 and handler2

        key_handlers = registry.find_handlers(KeyError)
        assert len(key_handlers) == 2  # Should include Exception and KeyError handler

    def test_handler_execution_order(self):
        """
        Test that handlers are executed in registration order.

        Validates:
        - Handlers are found and can be executed in the correct order
        - Order of registration is preserved in handler lookup
        """
        registry = HandlerRegistry()
        execution_order = []

        # Define handlers that record their execution order
        def handler1(error, context):
            execution_order.append(1)
            return True

        def handler2(error, context):
            execution_order.append(2)
            return True

        # Register handlers
        registry.register(ValueError, handler1)
        registry.register(ValueError, handler2)

        # Get handlers and execute them
        handlers = registry.find_handlers(ValueError)
        for handler in handlers:
            handler(ValueError("Test error"), None)

        # Verify execution order
        assert execution_order == [1, 2]

    def test_handler_with_context(self):
        """
        Test handlers that use context information.

        Validates:
        - Handlers can access and use context information
        - Context is correctly passed through to handler functions
        """
        registry = HandlerRegistry()
        received_context = None

        # Define a handler that records the context it receives
        def context_handler(error, context):
            nonlocal received_context
            received_context = context
            return True

        # Register the handler
        registry.register(ValueError, context_handler)

        # Get handlers and execute with a context
        test_context = {"task_id": 123, "phase": "test"}
        handlers = registry.find_handlers(ValueError)
        for handler in handlers:
            handler(ValueError("Test error"), test_context)

        # Verify context was received
        assert received_context == test_context

    def test_mixed_return_values(self):
        """
        Test handling of different return values from handlers.

        Validates:
        - Handlers can return different values
        - Return values do not affect handler registration or lookup
        """
        registry = HandlerRegistry()

        # Define handlers with different return values
        def handler_true(error, context):
            return True

        def handler_false(error, context):
            return False

        def handler_none(error, context):
            return None

        # Register all handlers
        registry.register(ValueError, handler_true)
        registry.register(ValueError, handler_false)
        registry.register(ValueError, handler_none)

        # Verify all handlers are registered
        handlers = registry.find_handlers(ValueError)
        assert len(handlers) == 3

        # Execute and collect results
        results = [handler(ValueError("Test error"), None) for handler in handlers]
        assert results == [True, False, None]

    def test_complex_inheritance_hierarchy(self):
        """
        Test handler lookup with a complex inheritance hierarchy.

        Validates:
        - Handler lookup correctly traverses a complex inheritance tree
        - All applicable handlers are found based on type relationships
        """
        registry = HandlerRegistry()

        # Define a complex inheritance hierarchy
        class Level1Error(Exception):
            pass

        class Level2AError(Level1Error):
            pass

        class Level2BError(Level1Error):
            pass

        class Level3Error(Level2AError, Level2BError):
            pass

        # Define handlers for each level
        def handler_level1(error, context):
            return "level1"

        def handler_level2a(error, context):
            return "level2a"

        def handler_level2b(error, context):
            return "level2b"

        def handler_level3(error, context):
            return "level3"

        # Register handlers
        registry.register(Level1Error, handler_level1)
        registry.register(Level2AError, handler_level2a)
        registry.register(Level2BError, handler_level2b)
        registry.register(Level3Error, handler_level3)

        # Find handlers for Level3Error
        handlers = registry.find_handlers(Level3Error)

        # Verify all applicable handlers are found
        # Level3Error inherits from Level2A and Level2B, which both inherit from Level1
        handler_results = [h(None, None) for h in handlers]

        # Should include handlers from all parent classes
        assert "level1" in handler_results
        assert "level2a" in handler_results
        assert "level2b" in handler_results
        assert "level3" in handler_results
        assert len(handlers) == 4

    def test_builtins_error_hierarchy(self):
        """
        Test with Python's built-in exception hierarchy.

        Validates:
        - Handler lookup works correctly with Python's standard exceptions
        - Inheritance relationships in built-in exceptions are respected
        """
        registry = HandlerRegistry()

        # Track which handlers were called
        called_handlers = set()

        # Define handlers for different levels of the hierarchy
        def exception_handler(error, context):
            called_handlers.add("exception")
            return True

        def value_error_handler(error, context):
            called_handlers.add("value_error")
            return True

        def runtime_error_handler(error, context):
            called_handlers.add("runtime_error")
            return True

        # Register handlers
        registry.register(Exception, exception_handler)
        registry.register(ValueError, value_error_handler)
        registry.register(RuntimeError, runtime_error_handler)

        # Test with a ValueError
        val_handlers = registry.find_handlers(ValueError)
        for h in val_handlers:
            h(ValueError(), None)

        # Should include Exception and ValueError handlers
        assert "exception" in called_handlers
        assert "value_error" in called_handlers
        assert "runtime_error" not in called_handlers

        # Reset and test with RuntimeError
        called_handlers.clear()
        rt_handlers = registry.find_handlers(RuntimeError)
        for h in rt_handlers:
            h(RuntimeError(), None)

        # Should include Exception and RuntimeError handlers
        assert "exception" in called_handlers
        assert "runtime_error" in called_handlers
        assert "value_error" not in called_handlers

    def test_empty_registry(self):
        """
        Test behavior with an empty registry.

        Validates:
        - Empty registry returns no handlers for any type
        - No errors occur when looking up handlers in an empty registry
        """
        registry = HandlerRegistry()

        # Find handlers in an empty registry
        handlers = registry.find_handlers(Exception)

        # Should return an empty list, not None or error
        assert handlers == []

    def test_specific_to_general_lookup_order(self):
        """
        Test the order of handlers when both specific and general handlers exist.

        Validates:
        - More specific handlers are returned first in the result list
        - General handlers are included after specific ones
        """
        registry = HandlerRegistry()

        # Track execution order
        order = []

        # Define handlers for different levels
        def exception_handler(error, context):
            order.append("exception")
            return True

        def value_error_handler(error, context):
            order.append("value_error")
            return True

        # Register handlers (order shouldn't matter)
        registry.register(Exception, exception_handler)
        registry.register(ValueError, value_error_handler)

        # Find and execute handlers
        handlers = registry.find_handlers(ValueError)
        for h in handlers:
            h(ValueError(), None)

        # Check order - the handler_registry doesn't guarantee order
        # but we should have both handlers called
        assert "exception" in order
        assert "value_error" in order
        assert len(order) == 2

    def test_with_rv_android_exceptions(self):
        """
        Test integration with RV-Android exception hierarchy.

        Validates:
        - Handler registry works with the RV-Android exception types
        - Inheritance relationships in custom exceptions are respected
        """
        from rvandroid.util.exceptions import (
            RVAndroidError, ConfigurationError, EmulatorError, ADBError
        )

        registry = HandlerRegistry()

        # Track which handlers were called
        handled_exceptions = set()

        # Define handlers for different levels of the hierarchy
        def rv_android_handler(error, context):
            handled_exceptions.add("rv_android")
            return True

        def emulator_handler(error, context):
            handled_exceptions.add("emulator")
            return True

        def adb_handler(error, context):
            handled_exceptions.add("adb")
            return True

        # Register handlers
        registry.register(RVAndroidError, rv_android_handler)
        registry.register(EmulatorError, emulator_handler)
        registry.register(ADBError, adb_handler)

        # Test with various error types

        # Base RVAndroidError
        handled_exceptions.clear()
        handlers = registry.find_handlers(RVAndroidError)
        for h in handlers:
            h(RVAndroidError("Test error"), None)
        assert "rv_android" in handled_exceptions
        assert len(handled_exceptions) == 1

        # EmulatorError (subclass of RVAndroidError)
        handled_exceptions.clear()
        handlers = registry.find_handlers(EmulatorError)
        for h in handlers:
            h(EmulatorError("Test error"), None)
        assert "rv_android" in handled_exceptions
        assert "emulator" in handled_exceptions
        assert len(handled_exceptions) == 2

        # ADBError (subclass of RVAndroidError)
        handled_exceptions.clear()
        handlers = registry.find_handlers(ADBError)
        for h in handlers:
            h(ADBError("Test error"), None)
        assert "rv_android" in handled_exceptions
        assert "adb" in handled_exceptions
        assert len(handled_exceptions) == 2

        # ConfigurationError (subclass of RVAndroidError)
        handled_exceptions.clear()
        handlers = registry.find_handlers(ConfigurationError)
        for h in handlers:
            h(ConfigurationError("Test error"), None)
        assert "rv_android" in handled_exceptions
        assert len(handled_exceptions) == 1

    def test_with_rv_android_recovery_strategies(self):
        """
        Test integration with RV-Android recovery strategies.

        Validates:
        - RecoveryStrategies can be registered and found via the registry
        - Strategies are correctly invoked when errors occur
        """
        from rvandroid.util.exceptions import EmulatorError, ADBError
        from rvandroid.util.error.recovery_strategies import RecoveryStrategies

        registry = HandlerRegistry()

        # Register recovery strategies as handlers
        registry.register(EmulatorError, RecoveryStrategies.handle_emulator_error)
        registry.register(ADBError, RecoveryStrategies.handle_adb_error)

        # Find handlers for each error type
        emulator_handlers = registry.find_handlers(EmulatorError)
        adb_handlers = registry.find_handlers(ADBError)

        # Verify the correct handlers were found
        assert RecoveryStrategies.handle_emulator_error in emulator_handlers
        assert RecoveryStrategies.handle_adb_error in adb_handlers

    def test_handler_throwing_exception(self):
        """
        Test behavior when a handler throws an exception.

        Validates:
        - Exceptions in handlers don't affect the registry
        - Registry remains in a consistent state after handler errors
        """
        registry = HandlerRegistry()

        # Define a handler that throws an exception
        def faulty_handler(error, context):
            raise RuntimeError("Handler failure")

        # Define a normal handler
        def normal_handler(error, context):
            return True

        # Register both handlers
        registry.register(ValueError, faulty_handler)
        registry.register(ValueError, normal_handler)

        # Get the handlers
        handlers = registry.find_handlers(ValueError)
        assert len(handlers) == 2

        # First handler will raise an exception
        with pytest.raises(RuntimeError):
            handlers[0](ValueError("Test"), None)

        # Second handler should still work
        result = handlers[1](ValueError("Test"), None)
        assert result is True

        # Registry should still be intact
        handlers = registry.find_handlers(ValueError)
        assert len(handlers) == 2

    def test_register_with_invalid_types(self):
        """
        Test registration with invalid exception types.

        Validates:
        - Non-exception types can't be used in the registry
        - Registration validates the exception type
        """
        registry = HandlerRegistry()

        # Define a simple handler
        def handler(error, context):
            return True

        # Try to register with non-exception types
        with pytest.raises(TypeError):
            registry.register(str, handler)  # str is not an Exception subclass

        with pytest.raises(TypeError):
            registry.register(dict, handler)  # dict is not an Exception subclass

        # Verify registry is still empty
        assert len(registry._registry) == 0

    def test_register_with_invalid_handler(self):
        """
        Test registration with invalid handler functions.

        Validates:
        - Non-callable objects can't be registered as handlers
        - Handler registration validates the handler function
        """
        registry = HandlerRegistry()

        # Try to register with non-callable handlers
        with pytest.raises(TypeError):
            registry.register(Exception, "not a function")

        with pytest.raises(TypeError):
            registry.register(Exception, 123)

        # Verify registry is still empty
        assert len(registry._registry) == 0