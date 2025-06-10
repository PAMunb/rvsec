# rvandroid/util/error/decorators.py
import logging
import time
from functools import wraps
from typing import List, Type, Optional, Dict, Any, Callable

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.exceptions import ADBError, EmulatorError, RVAndroidError
from rv_android_core.util.logging.manager import LoggingManager


def retry(max_attempts: int = 3,
          retry_exceptions: List[Type[Exception]] = None,
          delay: float = 1.0,
          backoff_factor: float = 2.0,
          log_retries: bool = True):
    """
    Decorator to automatically retry a function on specified exceptions.

    Args:
        max_attempts: Maximum number of retry attempts
        retry_exceptions: List of exception types to retry on
        delay: Initial delay between retries in seconds
        backoff_factor: Factor to increase delay with each retry
        log_retries: Whether to log retry attempts

    Returns:
        Decorated function
    """
    if retry_exceptions is None:
        retry_exceptions = [ADBError, EmulatorError]

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get logger from LoggingManager
            logger = LoggingManager.get_instance().get_logger(
                'util.error.decorators.retry',
                {'function': func.__name__}
            )

            current_delay = delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except tuple(retry_exceptions) as e:
                    last_exception = e

                    if attempt < max_attempts - 1:
                        wait_time = current_delay
                        if log_retries:
                            logger.warning(
                                f"Attempt {attempt + 1}/{max_attempts} failed with {type(e).__name__}: {e}. "
                                f"Retrying in {wait_time:.2f}s..."
                            )

                        time.sleep(wait_time)
                        current_delay *= backoff_factor
                    else:
                        if log_retries:
                            logger.error(f"All {max_attempts} attempts failed")

            # Re-raise the last exception
            raise last_exception

        return wrapper

    return decorator


def handle_error(level: str = "ERROR",
                 context_builder: Optional[Callable[..., Dict[str, Any]]] = None,
                 raise_on_unhandled: bool = False,
                 error_types: Optional[List[Type[Exception]]] = None):
    """
    Decorator to handle exceptions using the centralized error handling system.
    
    ### Architectural Decisions:
    - Integrates with the centralized ErrorHandler for consistent error management
    - Provides detailed contextual information for effective error troubleshooting
    - Supports selective error handling based on error types
    - Enables optional automatic error recovery via the error handler
    
    ### Usage:
    - Apply to functions or methods that need standardized error handling
    - Configure error severity level appropriate to the function's criticality
    - Optionally provide a context_builder to supply additional error context
    
    Args:
        level: Logging level for errors (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        context_builder: Optional function to build context dictionary from function args
        raise_on_unhandled: Whether to re-raise exceptions that weren't handled
        error_types: List of exception types to handle, None for all exceptions
        
    Returns:
        Decorated function
    """
    log_level = getattr(logging, level.upper(), logging.ERROR)

    if error_types is None:
        error_types = [Exception]

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get the error handler singleton
            error_handler = ErrorHandler.get_instance()

            # Get logger from LoggingManager
            logger = LoggingManager.get_instance().get_logger(
                f'util.error.decorators.handle_error.{func.__module__}.{func.__name__}',
                {'function': func.__name__}
            )

            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Check if this is an error type we should handle
                if not any(isinstance(e, err_type) for err_type in error_types):
                    raise

                # Build context if a builder is provided
                context = {}
                if context_builder:
                    try:
                        context = context_builder(*args, **kwargs)
                    except Exception as context_error:
                        logger.warning(f"Error building context: {context_error}")

                # Add function information to context
                context.update({
                    'function': func.__name__,
                    'module': func.__module__,
                    'error_level': level
                })

                # Add 'self' class name if this is a method
                if args and hasattr(args[0], '__class__'):
                    context['class'] = args[0].__class__.__name__

                # Handle the error
                handled = error_handler.handle_error(e, context)

                # Log at the appropriate level
                log_method = getattr(logger, level.lower(), logger.error)
                log_method(f"Exception in {func.__name__}: {e}")

                # Re-raise if configured to do so and not handled
                if raise_on_unhandled and not handled:
                    # Optionally wrap in RVAndroidError with context
                    if not isinstance(e, RVAndroidError):
                        wrapped_error = RVAndroidError(
                            message=f"Unhandled error in {func.__name__}",
                            cause=e,
                            context=context
                        )
                        raise wrapped_error
                    else:
                        raise

                # Return None or some default value when error is handled
                # but we don't re-raise
                return None

        return wrapper

    return decorator


def log_execution_time(level: str = "DEBUG"):
    """
    Decorator to log the execution time of a function.
    
    Args:
        level: Logging level for timing information
        
    Returns:
        Decorated function
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get logger from LoggingManager
            logger = LoggingManager.get_instance().get_logger(
                'util.error.decorators.log_execution_time',
                {'function': func.__name__}
            )

            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed_time = time.time() - start_time

            # Log at the appropriate level
            log_method = getattr(logger, level.lower(), logger.debug)
            log_method(f"{func.__name__} executed in {elapsed_time:.6f} seconds")

            return result

        return wrapper

    return decorator
