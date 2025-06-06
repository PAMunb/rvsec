# rvandroid/util/logging/context_adapter.py
import logging
import threading
from datetime import datetime
from typing import Dict, Any, List

from rv_android_core.util.logging.constants import EXPERIMENT_START, EXPERIMENT_END, TASK_START, TASK_END


class ContextAdapter(logging.LoggerAdapter):
    """
    A logging adapter that adds contextual information to log records.
    Supports nested contexts and automatic propagation.
    """

    def __init__(self, logger, context=None):
        """
        Initialize the adapter with a logger and optional context.

        Args:
            logger: The logger to adapt
            context: Initial context dictionary
        """
        super().__init__(logger, {})
        self.context = context or {}
        self._context_stack: List[Dict[str, Any]] = []

    def process(self, msg, kwargs):
        """
        Process the log message by adding context information.

        Args:
            msg: The log message
            kwargs: Keyword arguments for the logger

        Returns:
            Tuple of (modified message, modified kwargs)
        """
        if 'extra' not in kwargs:
            kwargs['extra'] = {}

        # Add thread ID and timestamp to extra fields
        thread_id = threading.current_thread().ident
        if thread_id:
            kwargs['extra']['thread_id'] = thread_id

        kwargs['extra']['timestamp'] = datetime.now().isoformat()

        # Include context data
        for key, value in self.context.items():
            kwargs['extra'][key] = value

        return msg, kwargs

    def push_context(self, **context):
        """
        Push a new context onto the stack.

        Args:
            **context: Context key-value pairs
        """
        # Save current context
        self._context_stack.append(self.context.copy())

        # Update with new context
        self.context.update(context)

        return self

    def pop_context(self):
        """
        Pop the top context from the stack.

        Returns:
            The popped context
        """
        if not self._context_stack:
            return {}

        # Restore previous context
        old_context = self.context
        self.context = self._context_stack.pop()

        return old_context

    def with_context(self, **context):
        """
        Context manager for temporary context.

        Args:
            **context: Context key-value pairs

        Returns:
            Self for use in with statement
        """
        self.push_context(**context)
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.pop_context()

    # Add methods for custom log levels
    def experiment_start(self, msg, *args, **kwargs):
        self.log(EXPERIMENT_START, msg, *args, **kwargs)

    def experiment_end(self, msg, *args, **kwargs):
        self.log(EXPERIMENT_END, msg, *args, **kwargs)

    def task_start(self, msg, *args, **kwargs):
        self.log(TASK_START, msg, *args, **kwargs)

    def task_end(self, msg, *args, **kwargs):
        self.log(TASK_END, msg, *args, **kwargs)
