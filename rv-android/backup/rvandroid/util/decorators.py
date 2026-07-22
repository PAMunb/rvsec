# rvandroid/util/decorators.py
import functools
from typing import Callable

from rvandroid.util.error import handle_errors
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


def task_phase(phase_name: str, measure_performance: bool = True, handle_task_errors: bool = True):
    """
    Decorator for task execution phases that automatically handles logging, performance
    monitoring, and error handling.

    ### Architectural Decision:
    - Centralizes phase management for task execution
    - Reduces code duplication and nested context blocks
    - Provides consistent error handling and performance tracking

    Args:
        phase_name: Name of the execution phase
        measure_performance: Whether to measure performance for this phase
        handle_task_errors: Whether to handle errors using the error handler

    Returns:
        Decorated function
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Get standardized context for this phase
            context = self._get_task_context() if hasattr(self, '_get_task_context') else {}
            context.update({"phase": phase_name})

            # Set up logging context
            with self.logger.with_context(**context):
                self.logger.debug(f"Starting phase: {phase_name}")

                # Optional performance monitoring
                if measure_performance and hasattr(self, 'performance_monitor'):
                    with self.performance_monitor.measure_time(phase_name, context):
                        # Optional error handling
                        if handle_task_errors:
                            with handle_errors(context):
                                return func(self, *args, **kwargs)
                        else:
                            return func(self, *args, **kwargs)
                else:
                    # Just error handling without performance monitoring
                    if handle_task_errors:
                        with handle_errors(context):
                            return func(self, *args, **kwargs)
                    else:
                        return func(self, *args, **kwargs)

        return wrapper

    return decorator


def log_execution(logger_prefix: str, component_name: str = None):
    """
    Class decorator that sets up standardized logging for execution classes.

    Args:
        logger_prefix: Prefix for the logger name
        component_name: Optional component name for context

    Returns:
        Decorated class
    """

    def decorator(cls):
        original_init = cls.__init__

        def new_init(self, *args, **kwargs):
            # Set up logging using LoggingManager
            logging_manager = LoggingManager.get_instance()

            # Get context from instance attributes if possible
            context = {}
            if component_name:
                context[CONTEXT_COMPONENT] = component_name

            self.logger = logging_manager.get_logger(
                f"{logger_prefix}.{cls.__name__}",
                context
            )

            # Call original init
            original_init(self, *args, **kwargs)

        cls.__init__ = new_init
        return cls

    return decorator
