# rvandroid/util/logging/manager.py
import os
import sys
import threading
import time
from typing import Dict, Any, Optional

from rv_android_core.util.logging import constants
from rv_android_core.util.logging.context_adapter import ContextAdapter
from rv_android_core.util.logging.formatters import JsonFormatter, StructuredFormatter


class LoggingManager:
    """
    Centralized logging management system for RV-Android Framework.

    ### Architectural Decisions:
    - Implements a singleton pattern for global access to logging functionality
    - Delegates formatting, context handling to specialized components
    - Provides a consistent interface for all logging operations
    - Supports flexible configuration and extension

    ### Role in the System:
    - Serves as the central hub for all logging operations
    - Provides unified logging interface across all components
    - Enables contextual debugging through structured log data
    - Facilitates troubleshooting through consistent log formats
    """

    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        """Get the singleton instance of the logging manager."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = LoggingManager()
            return cls._instance

    def __init__(self):
        """Initialize the logging manager."""
        self.root_logger = constants.logging.getLogger('rvandroid')
        self.log_path = None
        self.logger_cache = {}
        self.context_registry = {}
        self._output_config = {
            'console': {
                'enabled': True,
                'level': constants.logging.INFO,
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
            'file': {
                'enabled': False,
                'level': constants.logging.DEBUG,
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'json': False
            }
        }

        # Check if root logger already has handlers (set up by basicConfig)
        # If it does, we don't need to add our own to avoid duplication
        root_has_handlers = len(constants.logging.getLogger().handlers) > 0

        if not root_has_handlers and len(self.root_logger.handlers) == 0:
            self._setup_default_logging()

    def _setup_default_logging(self):
        """Configure default logging to console."""
        # Clear existing handlers
        self.root_logger.handlers = []

        # Console handler
        if self._output_config['console']['enabled']:
            console_handler = constants.logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self._output_config['console']['level'])

            # Regular formatter for console
            formatter = constants.logging.Formatter(self._output_config['console']['format'])
            console_handler.setFormatter(formatter)

            # Add handler to root logger
            self.root_logger.addHandler(console_handler)

        # Prevent propagation to the root logger to avoid duplicate logs
        # Only do this if we've added our own handlers
        self.root_logger.propagate = False

        # Set the overall logger level to the minimum of all handlers
        min_level = min(
            self._output_config['console']['level'] if self._output_config['console'][
                'enabled'] else constants.logging.CRITICAL,
            self._output_config['file']['level'] if self._output_config['file'][
                'enabled'] else constants.logging.CRITICAL
        )
        self.root_logger.setLevel(min_level)

    def configure_output(self, console=True, file=False, console_level=constants.logging.INFO,
                         file_level=constants.logging.DEBUG, json_format=False,
                         console_format=None, file_format=None):
        """
        Configure logging output destinations and formats.

        Args:
            console: Whether to enable console output
            file: Whether to enable file output
            console_level: Logging level for console
            file_level: Logging level for file
            json_format: Whether to use JSON format for file logs
            console_format: Format string for console logs
            file_format: Format string for file logs
        """
        self._output_config['console']['enabled'] = console
        self._output_config['console']['level'] = console_level
        if console_format:
            self._output_config['console']['format'] = console_format

        self._output_config['file']['enabled'] = file
        self._output_config['file']['level'] = file_level
        self._output_config['file']['json'] = json_format
        if file_format:
            self._output_config['file']['format'] = file_format

        # Reconfigure logging
        self._setup_default_logging()

        # Update any existing file logging
        if self.log_path:
            self.setup_file_logging(os.path.dirname(self.log_path),
                                    os.path.basename(self.log_path),
                                    self._output_config['file']['json'])

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

        # Remove any existing file handlers
        for handler in self.root_logger.handlers[:]:
            if isinstance(handler, constants.logging.FileHandler):
                self.root_logger.removeHandler(handler)

        # File handler
        file_handler = constants.logging.FileHandler(self.log_path)
        file_handler.setLevel(self._output_config['file']['level'])

        # Choose formatter based on format
        if json_format:
            formatter = JsonFormatter()
        else:
            formatter = StructuredFormatter(self._output_config['file']['format'])

        file_handler.setFormatter(formatter)

        # Add handler to root logger
        self.root_logger.addHandler(file_handler)

        # Update file config
        self._output_config['file']['enabled'] = True

    def get_logger(self, name: str, context: Optional[Dict[str, Any]] = None):
        """
        Get a logger with the given name and context.

        Args:
            name: Logger name
            context: Optional context dictionary to add to all log records

        Returns:
            Logger with context adapter
        """
        # Create a cache key based on name and context items
        cache_key = name
        if context:
            # Sort to ensure deterministic cache key
            context_items = sorted(context.items())
            cache_key = f"{name}:{context_items}"

        # Check cache first
        if cache_key in self.logger_cache:
            return self.logger_cache[cache_key]

        # Create new logger
        logger = constants.logging.getLogger(name)

        # Create adapter with context
        adapter = ContextAdapter(logger, context or {})

        # Cache the logger
        self.logger_cache[cache_key] = adapter

        # Register context if provided
        if context:
            self.register_context(name, context)

        return adapter

    def register_context(self, name: str, context: Dict[str, Any]):
        """
        Register a context with a logger name for future reference.

        Args:
            name: Logger name
            context: Context dictionary
        """
        self.context_registry[name] = context.copy()

    def get_context(self, name: str) -> Dict[str, Any]:
        """
        Get registered context for a logger name.

        Args:
            name: Logger name

        Returns:
            Context dictionary or empty dict if not found
        """
        return self.context_registry.get(name, {})
