# rvandroid/util/error/decorators.py
import time
from functools import wraps
from typing import List, Type

from rvandroid.util.exceptions import ADBError, EmulatorError
from rvandroid.util.logging.manager import LoggingManager


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
