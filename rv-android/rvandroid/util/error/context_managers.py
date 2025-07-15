# rvandroid/util/error/context_managers.py
from contextlib import contextmanager
from typing import Dict, Optional, Any

from rvandroid.util.error.error_handler import ErrorHandler


@contextmanager
def handle_errors(context: Optional[Dict[str, Any]] = None):
    """
    Context manager for handling errors with the central ErrorHandler.

    Args:
        context: Optional context information for the error

    Yields:
        Nothing

    Example:
        ```
        with handle_errors({"task_id": task.id}):
            # Code that might raise exceptions
            process_task(task)
        ```
    """
    handler = ErrorHandler.get_instance()
    try:
        yield
    except Exception as e:
        handler.handle_error(e, context)
        raise  # Re-raise the exception after handling
