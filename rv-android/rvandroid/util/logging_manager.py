import json
import logging
import os
import sys
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional

# Define custom log levels for experiment-specific events
EXPERIMENT_START = 25
EXPERIMENT_END = 26
TASK_START = 27
TASK_END = 28
ERROR = 40  # Same as logging.ERROR

# Register custom log levels with logging module
logging.addLevelName(EXPERIMENT_START, "EXPERIMENT_START")
logging.addLevelName(EXPERIMENT_END, "EXPERIMENT_END")
logging.addLevelName(TASK_START, "TASK_START")
logging.addLevelName(TASK_END, "TASK_END")


class ContextAdapter(logging.LoggerAdapter):
    """
    A logging adapter that adds contextual information to log records.
    """

    def process(self, msg, kwargs):
        if 'extra' not in kwargs:
            kwargs['extra'] = {}

        # Add thread ID and timestamp to extra fields
        thread_id = threading.current_thread().ident
        if thread_id:
            kwargs['extra']['thread_id'] = thread_id

        kwargs['extra']['timestamp'] = datetime.now().isoformat()

        # Include context data if available
        if hasattr(self, 'context'):
            for key, value in self.context.items():
                kwargs['extra'][key] = value

        return msg, kwargs


class JsonFormatter(logging.Formatter):
    """
    Formatter that outputs log records as JSON.
    """

    def format(self, record):
        log_data = {
            'timestamp': getattr(record, 'timestamp', datetime.now().isoformat()),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread_id': getattr(record, 'thread_id', threading.current_thread().ident),
        }

        # Include any extra fields from the record
        for key, value in record.__dict__.items():
            if key not in log_data and not key.startswith('_') and key != 'args' and key != 'msg':
                log_data[key] = value

        return json.dumps(log_data)


class LoggingManager:
    """
    Centralized logging manager for rv-android.
    Configures loggers, handlers, and formatters.
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = LoggingManager()
        return cls._instance

    def __init__(self):
        self.root_logger = logging.getLogger('rvandroid')
        self.log_path = None

        # Check if root logger already has handlers (set up by basicConfig)
        # If it does, we don't need to add our own to avoid duplication
        root_has_handlers = len(logging.getLogger().handlers) > 0

        if not root_has_handlers and len(self.root_logger.handlers) == 0:
            self.setup_default_logging()

    def setup_default_logging(self):
        """Configure default logging to console, only if no handlers exist."""
        # Clear existing handlers
        self.root_logger.handlers = []

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        # Regular formatter for console
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)

        # Add handler to root logger
        self.root_logger.addHandler(console_handler)

        # Prevent propagation to the root logger to avoid duplicate logs
        # Only do this if we've added our own handlers
        self.root_logger.propagate = False

    def setup_file_logging(self, log_dir: str, experiment_id: str, json_format: bool = False):
        """
        Set up file logging for an experiment.

        Args:
            log_dir: Directory for log files
            experiment_id: ID of the experiment
            json_format: Whether to use JSON formatting for logs
        """
        # Create log directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)

        # Create log file path
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        self.log_path = os.path.join(log_dir, f"{experiment_id}_{timestamp}.log")

        # File handler
        file_handler = logging.FileHandler(self.log_path)
        file_handler.setLevel(logging.DEBUG)

        # Choose formatter based on format
        if json_format:
            formatter = JsonFormatter()
        else:
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        file_handler.setFormatter(formatter)

        # Add handler to root logger
        self.root_logger.addHandler(file_handler)

    def get_logger(self, name: str, context: Optional[Dict[str, Any]] = None):
        """
        Get a logger with the given name and context.

        Args:
            name: Logger name
            context: Optional context dictionary to add to all log records

        Returns:
            Logger with context adapter
        """
        logger = logging.getLogger(f'rvandroid.{name}')

        # Create adapter with context
        adapter = ContextAdapter(logger, {})
        if context:
            adapter.context = context

        # Add convenience methods for custom log levels
        def experiment_start(self, msg, *args, **kwargs):
            self.log(EXPERIMENT_START, msg, *args, **kwargs)

        def experiment_end(self, msg, *args, **kwargs):
            self.log(EXPERIMENT_END, msg, *args, **kwargs)

        def task_start(self, msg, *args, **kwargs):
            self.log(TASK_START, msg, *args, **kwargs)

        def task_end(self, msg, *args, **kwargs):
            self.log(TASK_END, msg, *args, **kwargs)

        # Add methods to the adapter
        adapter.experiment_start = experiment_start.__get__(adapter)
        adapter.experiment_end = experiment_end.__get__(adapter)
        adapter.task_start = task_start.__get__(adapter)
        adapter.task_end = task_end.__get__(adapter)

        return adapter
