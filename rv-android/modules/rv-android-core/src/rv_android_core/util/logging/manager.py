# rvandroid/util/logging/manager.py
import os
import sys
import threading
import time
from typing import Dict, Any, Optional

from rv_android_core.util.logging import constants
from rv_android_core.util.logging.context_adapter import ContextAdapter
from rv_android_core.util.logging.formatters import JsonFormatter, StructuredFormatter
from rv_android_core.util.exceptions import ConfigurationError


class LoggingManager:
    """
    Centralized logging management system for RV-Android Framework.

    This class provides a unified interface for configuring and managing logging 
    across the entire framework. It handles both console and file output with 
    configurable formatting, context display, and structured logging capabilities.

    ### Architectural Decisions:
    - Implements singleton pattern for global access to logging functionality
    - Delegates formatting and context handling to specialized components
    - Provides consistent interface for all logging operations across components
    - Supports runtime configuration changes without system restart
    - Implements caching mechanism for logger instances to improve performance
    - Uses thread-safe operations for concurrent access scenarios

    ### Role in the System:
    - Serves as central hub for all logging operations within the framework
    - Provides unified logging interface across all system components
    - Enables contextual debugging through structured log data injection
    - Manages output destinations (console, file) with independent configuration
    - Facilitates troubleshooting through consistent log formats and context
    - Supports experiment tracking through custom log levels and metadata

    ### Key Features:
    - Context display control for enhanced debugging capabilities
    - Runtime configuration changes for logging behavior
    - Independent console and file output configuration
    - Custom log levels for experiment and task tracking
    - Thread-safe logger caching and context registry
    - Flexible formatter selection based on output requirements

    ### Integration Strategy:
    - Integrates with ContextAdapter for automatic context injection
    - Compatible with standard Python logging infrastructure
    - Supports custom formatters for different output requirements
    - Provides context registry for cross-component context sharing
    - Enables experiment workflow tracking through specialized log levels

    ### Performance Considerations:
    - Logger instance caching reduces object creation overhead
    - Context registry enables efficient context sharing across components
    - Conditional formatter selection optimizes performance based on requirements
    - Thread-safe singleton implementation prevents resource contention
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
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'show_context': True,
                'max_context_length': 120
            },
            'file': {
                'enabled': False,
                'level': constants.logging.DEBUG,
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'json': False,
                'show_context': True,
                'max_context_length': 200
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

            # Select formatter based on context display configuration
            if self._output_config['console']['show_context']:
                formatter = StructuredFormatter(
                    self._output_config['console']['format'],
                    max_context_length=self._output_config['console']['max_context_length']
                )
            else:
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
                         console_format=None, file_format=None, console_context=None,
                         file_context=None):
        """
        Configure logging output destinations and formats.

        This method provides comprehensive configuration of logging outputs including
        context display settings for both console and file destinations.

        Args:
            console: Whether to enable console output
            file: Whether to enable file output
            console_level: Logging level for console output
            file_level: Logging level for file output
            json_format: Whether to use JSON format for file logs
            console_format: Format string for console logs
            file_format: Format string for file logs
            console_context: Whether to show context in console (None = keep current)
            file_context: Whether to show context in file (None = keep current)
        """
        self._output_config['console']['enabled'] = console
        self._output_config['console']['level'] = console_level
        if console_format:
            self._output_config['console']['format'] = console_format
        if console_context is not None:
            self._output_config['console']['show_context'] = console_context

        self._output_config['file']['enabled'] = file
        self._output_config['file']['level'] = file_level
        self._output_config['file']['json'] = json_format
        if file_format:
            self._output_config['file']['format'] = file_format
        if file_context is not None:
            self._output_config['file']['show_context'] = file_context

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

        # Choose formatter based on format and context display configuration
        if json_format:
            formatter = JsonFormatter()
        else:
            if self._output_config['file']['show_context']:
                formatter = StructuredFormatter(
                    self._output_config['file']['format'],
                    max_context_length=self._output_config['file']['max_context_length']
                )
            else:
                formatter = constants.logging.Formatter(self._output_config['file']['format'])

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

    def toggle_context_display(self, console=None, file=None):
        """
        Toggle context display for console and/or file output.

        This method allows runtime modification of context display settings without
        requiring system restart. It provides granular control over context visibility
        for different output destinations.

        Args:
            console: Enable/disable context display for console (None = no change)
            file: Enable/disable context display for file (None = no change)

        Raises:
            ConfigurationError: If invalid configuration parameters are provided
        """
        try:
            if console is not None:
                if not isinstance(console, bool):
                    raise ConfigurationError(
                        f"Console context display must be boolean, got {type(console).__name__}"
                    )
                self._output_config['console']['show_context'] = console
            
            if file is not None:
                if not isinstance(file, bool):
                    raise ConfigurationError(
                        f"File context display must be boolean, got {type(file).__name__}"
                    )
                self._output_config['file']['show_context'] = file
            
            # Reconfigure logging with new settings
            self._setup_default_logging()
            
            # Update file logging if active
            if self.log_path and self._output_config['file']['enabled']:
                self.setup_file_logging(
                    os.path.dirname(self.log_path),
                    os.path.basename(self.log_path).split('_')[0],
                    self._output_config['file']['json']
                )
        except Exception as e:
            raise ConfigurationError(f"Failed to toggle context display: {str(e)}", cause=e)

    def configure_context_display(self, console_context=None, file_context=None,
                                  console_max_length=None, file_max_length=None):
        """
        Configure context display settings for logging outputs.

        This method provides comprehensive configuration of context display behavior
        including visibility control and formatting constraints for both console and
        file output destinations.

        Args:
            console_context: Enable/disable context display for console
            file_context: Enable/disable context display for file
            console_max_length: Maximum context length for console output
            file_max_length: Maximum context length for file output

        Raises:
            ConfigurationError: If invalid configuration parameters are provided
        """
        try:
            # Validate and update console context settings
            if console_context is not None:
                if not isinstance(console_context, bool):
                    raise ConfigurationError(
                        f"Console context display must be boolean, got {type(console_context).__name__}"
                    )
                self._output_config['console']['show_context'] = console_context
            
            if console_max_length is not None:
                if not isinstance(console_max_length, int) or console_max_length < 1:
                    raise ConfigurationError(
                        f"Console max context length must be positive integer, got {console_max_length}"
                    )
                self._output_config['console']['max_context_length'] = console_max_length
            
            # Validate and update file context settings
            if file_context is not None:
                if not isinstance(file_context, bool):
                    raise ConfigurationError(
                        f"File context display must be boolean, got {type(file_context).__name__}"
                    )
                self._output_config['file']['show_context'] = file_context
            
            if file_max_length is not None:
                if not isinstance(file_max_length, int) or file_max_length < 1:
                    raise ConfigurationError(
                        f"File max context length must be positive integer, got {file_max_length}"
                    )
                self._output_config['file']['max_context_length'] = file_max_length
            
            # Reconfigure logging with new settings
            self._setup_default_logging()
            
            # Update file logging if active
            if self.log_path and self._output_config['file']['enabled']:
                self.setup_file_logging(
                    os.path.dirname(self.log_path),
                    os.path.basename(self.log_path).split('_')[0],
                    self._output_config['file']['json']
                )
        except Exception as e:
            raise ConfigurationError(f"Failed to configure context display: {str(e)}", cause=e)

    def get_context_display_config(self):
        """
        Get current context display configuration.

        Returns a dictionary containing the current context display settings for
        both console and file output destinations.

        Returns:
            Dict[str, Dict[str, Any]]: Current context display configuration
        """
        return {
            'console': {
                'show_context': self._output_config['console']['show_context'],
                'max_context_length': self._output_config['console']['max_context_length']
            },
            'file': {
                'show_context': self._output_config['file']['show_context'],
                'max_context_length': self._output_config['file']['max_context_length']
            }
        }
